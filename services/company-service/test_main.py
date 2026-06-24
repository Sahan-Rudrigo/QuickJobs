"""
Company Service — unit + integration tests.
Requires PostgreSQL running at localhost:5433 (docker compose up -d postgres).
Auth is bypassed via dependency override so no Cognito token is needed.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SKIP_AUTH", "true")

from main import app
from database import Base, get_db
from auth import get_token_payload

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://admin:password123@localhost:5433/quickjobs",
)

engine      = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def mock_admin_payload():
    return {"sub": "test-admin-sub", "cognito:groups": ["quickjobs-admins"]}


def mock_employer_payload():
    return {"sub": "test-employer-sub", "cognito:groups": ["quickjobs-employers"]}


app.dependency_overrides[get_db]            = override_get_db
app.dependency_overrides[get_token_payload] = mock_admin_payload

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    yield
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM job_matches"))
        conn.execute(text("DELETE FROM jobs"))
        conn.execute(text("DELETE FROM companies"))
        conn.commit()


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Company CRUD ──────────────────────────────────────────────────────────────

def test_create_company():
    res = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Acme Corp"
    assert data["status"] == "PENDING"
    assert data["id"]


def test_create_company_idempotent_by_cognito_sub():
    """Second POST with same cognito_user_id returns the existing company."""
    client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    })
    res = client.post("/companies", json={
        "name": "Acme Corp Duplicate", "email": "acme2@test.com",
        "cognito_user_id": "sub-acme",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "Acme Corp"


def test_create_company_idempotent_by_email():
    """Second POST with same email (different sub) returns the existing company."""
    client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    })
    res = client.post("/companies", json={
        "name": "Acme Corp B", "email": "acme@test.com",
        "cognito_user_id": "sub-other",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "Acme Corp"


def test_get_company_by_user():
    client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    })
    res = client.get("/companies/by-user/sub-acme")
    assert res.status_code == 200
    assert res.json()["cognito_user_id"] == "sub-acme"


def test_get_company_by_user_not_found():
    res = client.get("/companies/by-user/nonexistent-sub")
    assert res.status_code == 404


def test_get_company_by_id():
    created = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    res = client.get(f"/companies/{created['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


# ── Job posting ───────────────────────────────────────────────────────────────

@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_post_job_pending_company_blocked(mock_match, mock_sqs):
    """PENDING companies cannot post jobs."""
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    res = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    })
    assert res.status_code == 403


@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_post_job_approved_company(mock_match, mock_sqs):
    """APPROVED companies can post jobs."""
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    res = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Senior Developer", "location": "Colombo",
        "job_type": "Full-time", "description": "Build stuff.",
        "skills": ["Python", "React"],
    })
    assert res.status_code == 200
    job = res.json()
    assert job["title"] == "Senior Developer"
    assert job["status"] == "Active"
    assert job["applications"] == 0


@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=["94771234567", "94779876543"])
def test_post_job_with_matches(mock_match, mock_sqs):
    """When matching returns phones, applications count is updated and SQS published."""
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    res = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "Build stuff.",
        "skills": ["Python"],
    })
    assert res.status_code == 200
    assert res.json()["applications"] == 2
    mock_sqs.assert_called_once()


@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_get_company_jobs(mock_match, mock_sqs):
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    })
    client.post(f"/companies/{company['id']}/jobs", json={
        "title": "QA", "location": "Galle",
        "job_type": "Contract", "description": "test",
    })
    res = client.get(f"/companies/{company['id']}/jobs")
    assert res.status_code == 200
    assert len(res.json()) == 2


# ── Job actions ───────────────────────────────────────────────────────────────

@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_toggle_job_status(mock_match, mock_sqs):
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    job = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    }).json()

    toggled = client.patch(f"/jobs/{job['id']}/status").json()
    assert toggled["status"] == "Closed"

    toggled_back = client.patch(f"/jobs/{job['id']}/status").json()
    assert toggled_back["status"] == "Active"


@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_delete_job(mock_match, mock_sqs):
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    job = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    }).json()

    res = client.delete(f"/jobs/{job['id']}")
    assert res.status_code == 200

    jobs = client.get(f"/companies/{company['id']}/jobs").json()
    assert len(jobs) == 0


# ── Admin endpoints ───────────────────────────────────────────────────────────

def test_admin_approve_company():
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    res = client.patch(f"/admin/companies/{company['id']}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"


def test_admin_reject_company():
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    res = client.patch(f"/admin/companies/{company['id']}/reject")
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


def test_admin_suspend_company():
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    res = client.patch(f"/admin/companies/{company['id']}/suspend")
    assert res.status_code == 200
    assert res.json()["status"] == "SUSPENDED"


def test_admin_list_companies():
    client.post("/companies", json={"name": "A", "email": "a@test.com", "cognito_user_id": "sub-a"})
    client.post("/companies", json={"name": "B", "email": "b@test.com", "cognito_user_id": "sub-b"})
    res = client.get("/admin/companies")
    assert res.status_code == 200
    assert len(res.json()) >= 2


def test_admin_list_companies_filter_by_status():
    client.post("/companies", json={"name": "A", "email": "a@test.com", "cognito_user_id": "sub-a"})
    company_b = client.post("/companies", json={
        "name": "B", "email": "b@test.com", "cognito_user_id": "sub-b",
    }).json()
    client.patch(f"/admin/companies/{company_b['id']}/approve")

    res = client.get("/admin/companies?status=PENDING")
    statuses = [c["status"] for c in res.json()]
    assert all(s == "PENDING" for s in statuses)


def test_admin_stats():
    client.post("/companies", json={"name": "A", "email": "a@test.com", "cognito_user_id": "sub-a"})
    company_b = client.post("/companies", json={
        "name": "B", "email": "b@test.com", "cognito_user_id": "sub-b",
    }).json()
    client.patch(f"/admin/companies/{company_b['id']}/approve")

    res = client.get("/admin/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_companies" in data
    assert "pending_approvals" in data
    assert data["approved_companies"] >= 1


# ── Reverse matching (applicant add) ─────────────────────────────────────────

@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_add_applicant_to_job(mock_match, mock_sqs):
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    job = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    }).json()

    res = client.post(f"/jobs/{job['id']}/applicants", json={"phone": "94771234567"})
    assert res.status_code == 200
    assert res.json()["status"] == "added"

    updated = client.get(f"/companies/{company['id']}/jobs").json()
    assert updated[0]["applications"] == 1


@patch("routes.publish_job_matched")
@patch("routes._call_matching_service", return_value=[])
def test_add_applicant_idempotent(mock_match, mock_sqs):
    """Adding the same phone twice doesn't duplicate."""
    company = client.post("/companies", json={
        "name": "Acme Corp", "email": "acme@test.com",
        "cognito_user_id": "sub-acme",
    }).json()
    client.patch(f"/admin/companies/{company['id']}/approve")

    job = client.post(f"/companies/{company['id']}/jobs", json={
        "title": "Dev", "location": "Colombo",
        "job_type": "Full-time", "description": "test",
    }).json()

    client.post(f"/jobs/{job['id']}/applicants", json={"phone": "94771234567"})
    res = client.post(f"/jobs/{job['id']}/applicants", json={"phone": "94771234567"})
    assert res.json()["status"] == "already_matched"

    updated = client.get(f"/companies/{company['id']}/jobs").json()
    assert updated[0]["applications"] == 1
