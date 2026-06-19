from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Load embedding model once at startup — reused for all requests
model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))

# Fields whose change warrants a full re-embed
_RE_EMBED_FIELDS = {"skills", "experience_level", "cv_version", "job_type_preference"}


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


def should_re_embed(old_profile: dict, new_profile: dict) -> bool:
    """
    Return True if the diff between old and new profile touches fields that
    affect match quality and therefore require fresh Pinecone vectors.
    """
    for field in _RE_EMBED_FIELDS:
        if old_profile.get(field) != new_profile.get(field):
            return True
    return False


def embed_job(job_id: str, title: str, skills: list, description: str) -> dict:
    """Generate a single vector for a job posting."""
    combined = f"{title}. Skills needed: {', '.join(skills)}. {description}"
    return {
        "id": f"job_{job_id}",
        "values": embed_text(combined),
        "metadata": {"job_id": job_id}
    }