import pytest
import json
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db

# ── Test DB (SQLite in-memory) ────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_files.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_s3():
    with patch("routes.upload_cv", return_value="cvs/94771234567/v1/cv.pdf"), \
         patch("routes.delete_cv"), \
         patch("routes.get_presigned_url", return_value="https://s3.example.com/cv.pdf"):
        yield


@pytest.fixture(autouse=True)
def mock_sqs():
    with patch("routes.publish_cv_uploaded", return_value=True):
        yield


@pytest.fixture(autouse=True)
def mock_extractor():
    with patch("routes.extract_text", return_value=("John Doe\nPython Developer\nSkills: Python, React", "pdf")):
        yield


@pytest.fixture(autouse=True)
def clean_db():
    yield
    # Clean cv_records between tests
    db = TestSession()
    db.execute(__import__("sqlalchemy").text("DELETE FROM cv_records"))
    db.commit()
    db.close()


def make_pdf_upload(phone="94771234567", skills=None, experience="mid"):
    skills = skills or ["Python", "React"]
    return client.post(
        f"/cv/upload/{phone}",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        data={"skills": json.dumps(skills), "experience": experience},
    )


# ── Health ────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "file-service"


# ── Upload ────────────────────────────────────────────────────────────

def test_upload_pdf_success():
    r = make_pdf_upload()
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["phone"] == "94771234567"
    assert data["version"] == 1
    assert data["text_length"] > 0


def test_upload_increments_version():
    make_pdf_upload()
    with patch("routes.upload_cv", return_value="cvs/94771234567/v2/cv.pdf"):
        r = make_pdf_upload()
    assert r.json()["version"] == 2


def test_upload_docx_success():
    r = client.post(
        "/cv/upload/94771234567",
        files={"file": ("cv.docx", b"fake docx content",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"skills": json.dumps(["Python"]), "experience": "senior"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_upload_empty_text_returns_422():
    with patch("routes.extract_text", return_value=("", "pdf")):
        r = client.post(
            "/cv/upload/94771234567",
            files={"file": ("cv.pdf", b"", "application/pdf")},
            data={"skills": "[]", "experience": "mid"},
        )
    assert r.status_code == 422


def test_upload_enforces_max_3_versions():
    """After 3 uploads, the 4th should trigger deletion of the oldest."""
    phones = ["94770000001"]

    with patch("routes.upload_cv", side_effect=[
        "cvs/p/v1/cv.pdf", "cvs/p/v2/cv.pdf",
        "cvs/p/v3/cv.pdf", "cvs/p/v4/cv.pdf",
    ]):
        for _ in range(4):
            make_pdf_upload(phone=phones[0])

    from models import CVRecord
    db = TestSession()
    records = db.query(CVRecord).filter(CVRecord.phone == phones[0]).all()
    db.close()
    assert len(records) == 3


# ── GET /cv/{phone} ───────────────────────────────────────────────────

def test_get_cv_records_success():
    make_pdf_upload()
    r = client.get("/cv/94771234567")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 1
    assert r.json()[0]["version"] == 1


def test_get_cv_records_not_found():
    r = client.get("/cv/00000000000")
    assert r.status_code == 404


def test_get_cv_download_url():
    make_pdf_upload()
    r = client.get("/cv/94771234567/latest/download")
    assert r.status_code == 200
    assert "download_url" in r.json()
    assert r.json()["version"] == 1


def test_get_cv_download_url_not_found():
    r = client.get("/cv/99999999999/latest/download")
    assert r.status_code == 404
