import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

from embedder import embed_cv, index, upsert_user_vectors, should_re_embed
from matcher import find_matching_candidates
from llm_parser import parse_cv_smart
from sqs_consumer import poll_cv_queue

load_dotenv()

app = FastAPI(
    title="QuickJobs Matching Service",
    description="AI-powered job matching using vector embeddings",
    version="0.2.0"
)

# Track consumer thread status
consumer_running = False


# ── Startup Event ─────────────────────────────────────────────────

@app.on_event("startup")
def start_consumer():
    """Start SQS consumer as background thread when service starts."""
    global consumer_running
    thread = threading.Thread(
        target=poll_cv_queue,
        daemon=True  # dies automatically when main process stops
    )
    thread.start()
    consumer_running = True
    print("[INFO] SQS consumer thread started in background")


# ── Request/Response Schemas ──────────────────────────────────────

class CVUploadRequest(BaseModel):
    phone: str
    skills: List[str]
    experience: str
    full_text: str


class JobMatchRequest(BaseModel):
    job_id: str
    title: str
    skills: List[str]
    description: str


class MatchResponse(BaseModel):
    job_id: str
    matched_phones: List[str]
    total_matches: int


class ManualEmbedRequest(BaseModel):
    raw_text: str
    fallback_skills: List[str] = []
    fallback_experience: str = ""
    version: int = 1


# ── Health Check ──────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Check if service and consumer are running."""
    return {
        "status": "ok",
        "service": "matching-service",
        "version": "0.2.0",
        "consumer_running": consumer_running
    }


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/embed/cv")
def embed_candidate_cv(request: CVUploadRequest):
    """
    Embed a candidate CV using Phase 1 basic embedding.
    Called directly by File Service if needed.
    """
    try:
        vectors = embed_cv(
            phone=request.phone,
            skills=request.skills,
            experience=request.experience,
            full_text=request.full_text
        )
        index.upsert(vectors=vectors)
        return {
            "status": "success",
            "phone": request.phone,
            "vectors_stored": len(vectors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed/{phone}")
def manual_embed(phone: str, request: ManualEmbedRequest):
    """
    Manually trigger LLM-based embedding for a candidate.
    Used by teammates for testing without going through WhatsApp.

    Example:
        POST /embed/94771234567
        {
            "raw_text": "Full CV text here...",
            "fallback_skills": ["Python", "React"],
            "fallback_experience": "mid",
            "version": 1
        }
    """
    try:
        # Use smart LLM parser
        sections = parse_cv_smart(
            raw_text=request.raw_text,
            fallback_skills=request.fallback_skills,
            fallback_experience=request.fallback_experience
        )

        # Check if re-embedding is needed
        if not should_re_embed(phone, sections):
            return {
                "status": "skipped",
                "phone": phone,
                "reason": "CV change too small to re-embed"
            }

        # Store vectors in Pinecone
        upsert_user_vectors(phone, sections, request.version)

        return {
            "status": "success",
            "phone": phone,
            "version": request.version,
            "sections_preview": {
                "skills": sections["skills"][:100],
                "experience": sections["experience"][:100]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/match/job", response_model=MatchResponse)
def match_job_to_candidates(request: JobMatchRequest):
    """
    Given a job posting, find and return matching candidate phones.
    Called by Job Service after a job is posted.
    """
    try:
        matched_phones = find_matching_candidates(
            job_id=request.job_id,
            title=request.title,
            skills=request.skills,
            description=request.description
        )
        return MatchResponse(
            job_id=request.job_id,
            matched_phones=matched_phones,
            total_matches=len(matched_phones)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index/stats")
def get_index_stats():
    """Return Pinecone index statistics — useful for monitoring."""
    try:
        stats = index.describe_index_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))