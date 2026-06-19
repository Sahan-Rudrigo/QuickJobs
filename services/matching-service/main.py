from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import threading
import os
from dotenv import load_dotenv

from embedder import embed_cv, embed_job, should_re_embed, index
from matcher import find_matching_candidates
from sqs_consumer import poll_cv_queue

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start SQS consumer in a daemon thread so it doesn't block the server
    if os.getenv("SQS_CV_UPLOADED_URL"):
        t = threading.Thread(target=poll_cv_queue, daemon=True)
        t.start()
        print("[INFO] SQS consumer thread started")
    else:
        print("[WARN] SQS_CV_UPLOADED_URL not set — SQS consumer not started")
    yield


app = FastAPI(
    title="QuickJobs Matching Service",
    description="AI-powered job matching using vector embeddings",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request / Response Schemas ────────────────────────────────────────

class CVEmbedRequest(BaseModel):
    skills: List[str]
    experience: str
    full_text: str


class CVEmbedByPhoneRequest(BaseModel):
    """Same as CVEmbedRequest but phone comes from the URL path."""
    skills: List[str]
    experience: str
    full_text: str
    old_profile: Optional[dict] = None  # if provided, skip re-embed when unchanged


class JobMatchRequest(BaseModel):
    job_id: str
    title: str
    skills: List[str]
    description: str


class MatchResponse(BaseModel):
    job_id: str
    matched_phones: List[str]
    total_matches: int


# ── Health Check ──────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "matching-service"}


# ── CV Embedding Endpoints ─────────────────────────────────────────────

@app.post("/embed/{phone}")
def embed_by_phone(phone: str, request: CVEmbedByPhoneRequest):
    """
    Embed a candidate's profile and store vectors in Pinecone.
    Phone number is in the URL path.

    If old_profile is supplied and nothing embedding-relevant changed,
    the call is a no-op (returns cached=True).
    """
    if request.old_profile:
        new_profile = {
            "skills": request.skills,
            "experience_level": request.experience,
            "cv_version": request.old_profile.get("cv_version", 0),
        }
        if not should_re_embed(request.old_profile, new_profile):
            return {"status": "skipped", "phone": phone, "cached": True}

    try:
        vectors = embed_cv(
            phone=phone,
            skills=request.skills,
            experience=request.experience,
            full_text=request.full_text,
        )
        index.upsert(vectors=vectors)
        return {"status": "success", "phone": phone, "vectors_stored": len(vectors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed/cv")
def embed_candidate_cv(request: CVEmbedRequest, phone: str):
    """
    Legacy endpoint — prefer POST /embed/{phone}.
    Kept for backwards compatibility with any existing callers.
    """
    try:
        vectors = embed_cv(
            phone=phone,
            skills=request.skills,
            experience=request.experience,
            full_text=request.full_text,
        )
        index.upsert(vectors=vectors)
        return {"status": "success", "phone": phone, "vectors_stored": len(vectors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Job Matching Endpoint ──────────────────────────────────────────────

@app.post("/match/job", response_model=MatchResponse)
def match_job_to_candidates(request: JobMatchRequest):
    """
    Given a job posting, find and return matching candidate phones.
    Called by the Company Service after a job is posted.
    """
    try:
        matched_phones = find_matching_candidates(
            job_id=request.job_id,
            title=request.title,
            skills=request.skills,
            description=request.description,
        )
        return MatchResponse(
            job_id=request.job_id,
            matched_phones=matched_phones,
            total_matches=len(matched_phones),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Index Stats ────────────────────────────────────────────────────────

@app.get("/index/stats")
def get_index_stats():
    """Return Pinecone index statistics — useful for monitoring."""
    try:
        stats = index.describe_index_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
