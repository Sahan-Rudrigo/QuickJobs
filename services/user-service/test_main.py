import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from sqlalchemy import JSON

from main import app
from database import Base, get_db

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database  # Add this import
from unittest.mock import patch

from main import app
from database import Base, get_db

# ─────────────────────────────────────────
# TEST DATABASE SETUP
# Uses PostgreSQL. Auto-creates the database if missing!
# ─────────────────────────────────────────
TEST_DATABASE_URL = "postgresql://admin:password123@localhost:5433/quickjobs"

engine = create_engine(TEST_DATABASE_URL)

# 🚀 THE MAGIC FIX: If quickjobs_test doesn't exist, create it!
if not database_exists(engine.url):
    create_database(engine.url)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the real database with test database
app.dependency_overrides[get_db] = override_get_db

# Create test tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Mock Redis so tests don't need a real Redis running
@pytest.fixture(autouse=True)
def mock_redis():
    with patch("routes.set_opt_in_status"), \
         patch("routes.delete_opt_in_status"), \
         patch("redis_client.ping", return_value=True):
        yield


# ─────────────────────────────────────────
# HELPER — sample user data
# ─────────────────────────────────────────
def sample_user(phone="94771234567"):
    return {
        "phone": phone,
        "name": "Kasun Perera",
        "email": "kasun@example.com",
        "skills": ["Python", "React", "SQL"],
        "experience_level": "mid",
        "location": "Colombo",
        "salary_min": 80000,
        "salary_max": 150000,
        "availability": "actively_looking",
        "opt_in_status": True
    }


# ─────────────────────────────────────────
# HEALTH CHECK TEST
# ─────────────────────────────────────────
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "user-service"


# ─────────────────────────────────────────
# CREATE USER TESTS
# ─────────────────────────────────────────
def test_create_user_success():
    response = client.post("/users", json=sample_user("94771111111"))
    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == "94771111111"
    assert data["name"] == "Kasun Perera"
    assert data["skills"] == ["Python", "React", "SQL"]
    assert data["experience_level"] == "mid"
    assert data["opt_in_status"] == True


def test_create_user_duplicate_phone():
    # Create first time
    client.post("/users", json=sample_user("94772222222"))
    # Try to create again with same phone
    response = client.post("/users", json=sample_user("94772222222"))
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_user_missing_phone():
    response = client.post("/users", json={"name": "No Phone"})
    assert response.status_code == 422  # Validation error


def test_create_user_invalid_experience_level():
    user = sample_user("94773333333")
    user["experience_level"] = "expert"  # not a valid level
    response = client.post("/users", json=user)
    assert response.status_code == 422


# ─────────────────────────────────────────
# GET USER TESTS
# ─────────────────────────────────────────
def test_get_user_success():
    client.post("/users", json=sample_user("94774444444"))
    response = client.get("/users/94774444444")
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "94774444444"
    assert data["name"] == "Kasun Perera"


def test_get_user_not_found():
    response = client.get("/users/99999999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# ─────────────────────────────────────────
# UPDATE USER TESTS
# ─────────────────────────────────────────
def test_update_user_skills():
    client.post("/users", json=sample_user("94775555555"))
    response = client.patch(
        "/users/94775555555",
        json={"skills": ["Python", "Django", "AWS", "Docker"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Django" in data["skills"]
    assert "AWS" in data["skills"]
    # Other fields should be unchanged
    assert data["name"] == "Kasun Perera"
    assert data["location"] == "Colombo"


def test_update_user_location_only():
    client.post("/users", json=sample_user("94776666666"))
    response = client.patch(
        "/users/94776666666",
        json={"location": "Kandy"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Kandy"
    # Skills should be unchanged
    assert data["skills"] == ["Python", "React", "SQL"]


def test_update_cv_info():
    client.post("/users", json=sample_user("94777777777"))
    response = client.patch(
        "/users/94777777777",
        json={
            "cv_s3_key": "cvs/94777777777/v1/cv.pdf",
            "cv_version": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cv_s3_key"] == "cvs/94777777777/v1/cv.pdf"
    assert data["cv_version"] == 1


def test_update_user_not_found():
    response = client.patch("/users/00000000000", json={"name": "Ghost"})
    assert response.status_code == 404


# ─────────────────────────────────────────
# OPT OUT TESTS
# ─────────────────────────────────────────
def test_opt_out_success():
    client.post("/users", json=sample_user("94778888888"))
    response = client.patch("/users/94778888888/opt-out")
    assert response.status_code == 200
    data = response.json()
    assert data["opt_in_status"] == False
    assert data["phone"] == "94778888888"

    # Verify in database
    get_response = client.get("/users/94778888888")
    assert get_response.json()["opt_in_status"] == False
    assert get_response.json()["onboarding_state"] == "OPTED_OUT"


def test_opt_out_user_not_found():
    response = client.patch("/users/11111111111/opt-out")
    assert response.status_code == 404


# ─────────────────────────────────────────
# OPT IN TESTS
# ─────────────────────────────────────────
def test_opt_in_success():
    client.post("/users", json=sample_user("94779999999"))
    # First opt out
    client.patch("/users/94779999999/opt-out")
    # Then opt back in
    response = client.patch("/users/94779999999/opt-in")
    assert response.status_code == 200
    data = response.json()
    assert data["opt_in_status"] == True

    # Verify in database
    get_response = client.get("/users/94779999999")
    assert get_response.json()["opt_in_status"] == True
    assert get_response.json()["onboarding_state"] == "ACTIVE"


# ─────────────────────────────────────────
# DELETE USER TESTS
# ─────────────────────────────────────────
def test_delete_user_success():
    client.post("/users", json=sample_user("94770000001"))
    response = client.delete("/users/94770000001")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify user is gone
    get_response = client.get("/users/94770000001")
    assert get_response.status_code == 404


def test_delete_user_not_found():
    response = client.delete("/users/00000000001")
    assert response.status_code == 404


# ─────────────────────────────────────────
# GET ALL USERS TEST
# ─────────────────────────────────────────
def test_get_all_users():
    response = client.get("/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_all_users_pagination():
    response = client.get("/users?skip=0&limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5
