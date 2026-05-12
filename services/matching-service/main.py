from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

from embedder import embed_cv, index
from matcher import find_matching_candidates

load_dotenv()

app = FastAPI(
    title="QuickJobs Matching Service",
    description="AI-powered job matching using vector embeddings",
    version="0.1.0"
)


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


# ── Health Check ──────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Check if the service is running."""
    return {"status": "ok", "service": "matching-service"}


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/embed/cv")
def embed_candidate_cv(request: CVUploadRequest):
    """
    Receive a candidate's CV data and store embeddings in Pinecone.
    Called by the File Service after CV is uploaded.
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


@app.post("/match/job", response_model=MatchResponse)
def match_job_to_candidates(request: JobMatchRequest):
    """
    Given a job posting, find and return matching candidate phones.
    Called by the Job Service after a job is posted.
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