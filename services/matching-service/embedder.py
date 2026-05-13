from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

# Load embedding model once at startup — reused for all requests
model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))


def embed_text(text: str) -> list:
    """Convert any text into a 384-dimension vector."""
    return model.encode(text).tolist()


def embed_cv(phone: str, skills: list, experience: str, full_text: str) -> list:
    """Generate 3 vectors for a job seeker — skills, experience, summary."""
    return [
        {
            "id": f"{phone}_skills_v1",
            "values": embed_text(', '.join(skills)),
            "metadata": {"phone": phone, "section": "skills"}
        },
        {
            "id": f"{phone}_experience_v1",
            "values": embed_text(experience),
            "metadata": {"phone": phone, "section": "experience"}
        },
        {
            "id": f"{phone}_summary_v1",
            "values": embed_text(full_text[:2000]),
            "metadata": {"phone": phone, "section": "summary"}
        }
    ]


def embed_job(job_id: str, title: str, skills: list, description: str) -> dict:
    """Generate a single vector for a job posting."""
    combined = f"{title}. Skills needed: {', '.join(skills)}. {description}"
    return {
        "id": f"job_{job_id}",
        "values": embed_text(combined),
        "metadata": {"job_id": job_id}
    }


def upsert_user_vectors(phone: str, sections: dict, version: int):
    """
    Store 3 vectors in Pinecone for a candidate.
    Upsert means: insert if new, replace if already exists.

    Args:
        phone: candidate's WhatsApp number
        sections: dict with keys skills, experience, summary
        version: CV version number from File Service
    """
    vectors = [
        {
            "id": f"{phone}_skills",
            "values": embed_text(sections["skills"]),
            "metadata": {
                "phone": phone,
                "section": "skills",
                "version": version
            }
        },
        {
            "id": f"{phone}_experience",
            "values": embed_text(sections["experience"]),
            "metadata": {
                "phone": phone,
                "section": "experience",
                "version": version
            }
        },
        {
            "id": f"{phone}_summary",
            "values": embed_text(sections["summary"]),
            "metadata": {
                "phone": phone,
                "section": "summary",
                "version": version
            }
        }
    ]

    index.upsert(vectors=vectors)
    print(f"[INFO] Upserted 3 vectors for {phone} (CV version {version})")


def should_re_embed(phone: str, new_sections: dict) -> bool:
    """
    Check if CV changed enough to justify re-embedding.
    Prevents unnecessary re-embedding when user fixes a small typo.

    Returns True if re-embedding is needed, False if change is too small.
    """
    try:
        # Fetch existing summary vector from Pinecone
        result = index.fetch(ids=[f"{phone}_summary"])
        vectors = result.vectors

        # No existing vector — always embed
        if not vectors or f"{phone}_summary" not in vectors:
            print(f"[INFO] No existing vectors for {phone} — will embed")
            return True

        existing_vector = vectors[f"{phone}_summary"].values

        # Generate vector for new summary
        new_vector = embed_text(new_sections["summary"])

        # Calculate cosine similarity
        v1 = np.array(existing_vector)
        v2 = np.array(new_vector)
        similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

        # Cosine distance = 1 - similarity
        distance = 1 - similarity

        print(f"[INFO] CV change distance for {phone}: {distance:.4f}")

        # Re-embed only if change is significant
        if distance > 0.15:
            print(f"[INFO] Significant change detected — will re-embed")
            return True
        else:
            print(f"[INFO] Minor change — skipping re-embed")
            return False

    except Exception as e:
        print(f"[WARN] Error checking re-embed for {phone}: {e} — defaulting to embed")
        return True