import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_pinecone_index():
    """Replace the real Pinecone index with a mock for all tests."""
    mock_idx = MagicMock()
    mock_idx.upsert.return_value = None
    mock_idx.query.return_value = MagicMock(matches=[])
    mock_idx.describe_index_stats.return_value = {"dimension": 384, "total_vector_count": 0}
    with patch("embedder.index", mock_idx), patch("main.index", mock_idx):
        yield mock_idx


@pytest.fixture(autouse=True)
def mock_sentence_model():
    """Return a deterministic 384-dim vector without loading the real model."""
    fake_vector = [0.1] * 384
    with patch("embedder.model") as mock_model:
        mock_model.encode.return_value = fake_vector
        yield mock_model


# ── Health Check ──────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "matching-service"


# ── POST /embed/{phone} ───────────────────────────────────────────────

def test_embed_by_phone_success(mock_pinecone_index):
    response = client.post("/embed/94771234567", json={
        "skills": ["Python", "FastAPI"],
        "experience": "mid",
        "full_text": "Experienced Python developer with FastAPI skills.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["phone"] == "94771234567"
    assert data["vectors_stored"] == 3
    mock_pinecone_index.upsert.assert_called_once()


def test_embed_by_phone_skips_when_unchanged(mock_pinecone_index):
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    response = client.post("/embed/94771234567", json={
        "skills": ["Python"],
        "experience": "mid",
        "full_text": "Some text",
        "old_profile": old,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["cached"] is True
    mock_pinecone_index.upsert.assert_not_called()


def test_embed_by_phone_re_embeds_when_skills_change(mock_pinecone_index):
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    response = client.post("/embed/94771234567", json={
        "skills": ["Python", "React"],  # changed
        "experience": "mid",
        "full_text": "Some text",
        "old_profile": old,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_pinecone_index.upsert.assert_called_once()


def test_embed_by_phone_re_embeds_when_experience_changes(mock_pinecone_index):
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    response = client.post("/embed/94771234567", json={
        "skills": ["Python"],
        "experience": "senior",  # changed
        "full_text": "Some text",
        "old_profile": old,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_pinecone_index.upsert.assert_called_once()


# ── POST /match/job ───────────────────────────────────────────────────

def test_match_job_no_results(mock_pinecone_index):
    mock_pinecone_index.query.return_value = MagicMock(matches=[])
    response = client.post("/match/job", json={
        "job_id": "job_001",
        "title": "Python Developer",
        "skills": ["Python", "Django"],
        "description": "We need a Python developer.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_001"
    assert data["matched_phones"] == []
    assert data["total_matches"] == 0


def test_match_job_with_results(mock_pinecone_index):
    fake_match = MagicMock()
    fake_match.score = 0.85
    fake_match.metadata = {"phone": "94771234567"}
    mock_pinecone_index.query.return_value = MagicMock(matches=[fake_match])

    response = client.post("/match/job", json={
        "job_id": "job_002",
        "title": "React Developer",
        "skills": ["React", "TypeScript"],
        "description": "Frontend React role.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] == 1
    assert "94771234567" in data["matched_phones"]


def test_match_job_filters_below_threshold(mock_pinecone_index):
    low_score = MagicMock()
    low_score.score = 0.50  # below 0.72 threshold
    low_score.metadata = {"phone": "94779999999"}
    mock_pinecone_index.query.return_value = MagicMock(matches=[low_score])

    response = client.post("/match/job", json={
        "job_id": "job_003",
        "title": "Data Engineer",
        "skills": ["Spark", "Kafka"],
        "description": "Big data role.",
    })
    assert response.status_code == 200
    assert response.json()["total_matches"] == 0


# ── GET /index/stats ──────────────────────────────────────────────────

def test_index_stats(mock_pinecone_index):
    response = client.get("/index/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "stats" in data


# ── cv_parser unit tests ──────────────────────────────────────────────

from cv_parser import parse_cv_sections, extract_skills_from_text


def test_parse_cv_sections_with_headers():
    cv_text = """
John Doe

Summary
Experienced software developer with 5 years of experience.

Skills
Python, FastAPI, PostgreSQL, Docker

Experience
Software Engineer at TechCorp 2020-2024
Developed backend APIs using FastAPI.

Education
BSc Computer Science, University of Colombo, 2019
"""
    result = parse_cv_sections(cv_text)
    assert "Python" in result["skills_text"]
    assert "TechCorp" in result["experience_text"]
    assert "University" in result["education_text"]
    assert "Experienced software" in result["summary_text"]
    assert result["full_text"] == cv_text


def test_parse_cv_sections_fallback_to_full_text():
    cv_text = "No headers here. Just plain text about skills and experience."
    result = parse_cv_sections(cv_text)
    # Falls back to full text for all sections
    assert result["skills_text"] == cv_text
    assert result["experience_text"] == cv_text
    assert result["full_text"] == cv_text


def test_extract_skills_from_text():
    text = "Python • React • SQL | Docker, AWS"
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "React" in skills
    assert "SQL" in skills


def test_extract_skills_caps_at_30():
    text = ", ".join([f"Skill{i}" for i in range(50)])
    skills = extract_skills_from_text(text)
    assert len(skills) <= 30


# ── should_re_embed unit tests ────────────────────────────────────────

from embedder import should_re_embed


def test_should_re_embed_same_profile():
    profile = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    assert should_re_embed(profile, profile.copy()) is False


def test_should_re_embed_skills_changed():
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    new = {"skills": ["Python", "React"], "experience_level": "mid", "cv_version": 1}
    assert should_re_embed(old, new) is True


def test_should_re_embed_experience_changed():
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    new = {"skills": ["Python"], "experience_level": "senior", "cv_version": 1}
    assert should_re_embed(old, new) is True


def test_should_re_embed_cv_version_changed():
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1}
    new = {"skills": ["Python"], "experience_level": "mid", "cv_version": 2}
    assert should_re_embed(old, new) is True


def test_should_re_embed_location_change_ignored():
    old = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1, "location": "Colombo"}
    new = {"skills": ["Python"], "experience_level": "mid", "cv_version": 1, "location": "Kandy"}
    assert should_re_embed(old, new) is False
