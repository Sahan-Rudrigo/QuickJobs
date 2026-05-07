import sys
import os

# Allow imports from parent folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from embedder import embed_text, embed_cv, embed_job


def test_embed_text_returns_384_dimensions():
    """Every embedding must be exactly 384 numbers."""
    result = embed_text("Python developer with React experience")
    assert len(result) == 384, f"Expected 384, got {len(result)}"


def test_embed_text_returns_list_of_floats():
    """Embedding values must be floats, not strings or integers."""
    result = embed_text("Software engineer")
    assert isinstance(result, list)
    assert isinstance(result[0], float)


def test_similar_texts_have_high_score():
    """Two similar job descriptions should produce close vectors."""
    import numpy as np

    vec1 = embed_text("Python backend developer")
    vec2 = embed_text("Python software engineer")

    # Cosine similarity calculation
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    score = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    assert score > 0.7, f"Expected score > 0.7, got {score}"


def test_unrelated_texts_have_low_score():
    """Two unrelated texts should produce distant vectors."""
    import numpy as np

    vec1 = embed_text("Python backend developer")
    vec2 = embed_text("Chef cooking Italian food")

    v1 = np.array(vec1)
    v2 = np.array(vec2)
    score = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    assert score < 0.5, f"Expected score < 0.5, got {score}"


def test_embed_cv_returns_three_vectors():
    """Each candidate must have exactly 3 vectors."""
    result = embed_cv(
        phone="94771234567",
        skills=["Python", "React", "SQL"],
        experience="3 years backend developer",
        full_text="Experienced developer with strong backend skills"
    )
    assert len(result) == 3


def test_embed_cv_vector_ids_are_correct():
    """Vector IDs must follow the naming convention."""
    phone = "94771234567"
    result = embed_cv(
        phone=phone,
        skills=["Python"],
        experience="Junior developer",
        full_text="Recent graduate"
    )
    ids = [v["id"] for v in result]
    assert f"{phone}_skills_v1" in ids
    assert f"{phone}_experience_v1" in ids
    assert f"{phone}_summary_v1" in ids


def test_embed_job_returns_single_vector():
    """Job posting must produce exactly one vector."""
    result = embed_job(
        job_id="job123",
        title="Backend Developer",
        skills=["Python", "FastAPI"],
        description="Looking for an experienced backend engineer"
    )
    assert result["id"] == "job_job123"
    assert len(result["values"]) == 384