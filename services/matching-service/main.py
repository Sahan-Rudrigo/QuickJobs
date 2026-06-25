import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import threading
from dotenv import load_dotenv

from embedder import embed_cv, embed_job, embed_job_to_pinecone, delete_job_from_pinecone, should_re_embed, index
from matcher import find_matching_candidates, find_matching_jobs
from sqs_consumer import poll_cv_queue

load_dotenv()

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ────────────────────────────────────────────────

class CVEmbedByPhoneRequest(BaseModel):
    skills:      List[str]
    experience:  str
    full_text:   str
    old_profile: Optional[dict] = None


class CVEmbedRequest(BaseModel):
    skills:     List[str]
    experience: str
    full_text:  str


class JobMatchRequest(BaseModel):
    job_id:      str
    title:       str
    skills:      List[str]
    description: str


class MatchResponse(BaseModel):
    job_id:         str
    matched_phones: List[str]
    total_matches:  int


class JobEmbedRequest(BaseModel):
    job_id:      str
    title:       str
    skills:      List[str]
    description: str


class CandidateMatchRequest(BaseModel):
    phone:      str
    skills:     List[str]
    experience: str
    full_text:  str


class CandidateMatchResponse(BaseModel):
    phone:           str
    matched_job_ids: List[str]
    total_matches:   int


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "matching-service"}


# ── Job embedding (enables reverse matching) ──────────────────────────────────
# NOTE: static routes /embed/cv and /embed/job must be registered BEFORE the
# parameterised /embed/{phone} route, otherwise FastAPI matches them as phone="cv"
# or phone="job" and returns 422.

@app.post("/embed/cv")
def embed_candidate_cv(request: CVEmbedRequest, phone: str):
    """Legacy endpoint — prefer POST /embed/{phone}."""
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


@app.post("/embed/job")
def embed_job_endpoint(request: JobEmbedRequest):
    """
    Store a job vector in Pinecone.
    Called by Company Service when a job is posted.
    Enables reverse candidate-to-job matching for new CV uploads.
    """
    try:
        embed_job_to_pinecone(
            job_id=request.job_id,
            title=request.title,
            skills=request.skills,
            description=request.description,
        )
        return {"status": "success", "job_id": request.job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Candidate embedding ───────────────────────────────────────────────────────

@app.post("/embed/{phone}")
def embed_by_phone(phone: str, request: CVEmbedByPhoneRequest):
    """Embed a candidate's profile and store vectors in Pinecone."""
    if request.old_profile:
        new_profile = {
            "skills":           request.skills,
            "experience_level": request.experience,
            "cv_version":       request.old_profile.get("cv_version", 0),
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


# ── Job → candidates matching ─────────────────────────────────────────────────

@app.post("/match/job", response_model=MatchResponse)
def match_job_to_candidates(request: JobMatchRequest):
    """Given a job posting, find and return matching candidate phones."""
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


# ── Candidate → jobs matching (reverse) ──────────────────────────────────────

@app.post("/match/candidate", response_model=CandidateMatchResponse)
def match_candidate_to_jobs(request: CandidateMatchRequest):
    """
    Given a candidate profile, find matching active job IDs.
    Called by the SQS consumer after a CV is embedded.
    """
    try:
        matched_job_ids = find_matching_jobs(
            phone=request.phone,
            skills=request.skills,
            experience=request.experience,
            full_text=request.full_text,
        )
        return CandidateMatchResponse(
            phone=request.phone,
            matched_job_ids=matched_job_ids,
            total_matches=len(matched_job_ids),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Job vector deletion ───────────────────────────────────────────────────────

@app.delete("/embed/job/{job_id}")
def delete_job_embedding(job_id: str):
    """Remove a job's vector from Pinecone. Called by Company Service on job delete."""
    try:
        delete_job_from_pinecone(job_id)
        return {"status": "deleted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Index stats ───────────────────────────────────────────────────────────────

@app.get("/index/stats")
def get_index_stats():
    """Return Pinecone index statistics — useful for monitoring."""
    try:
        stats = index.describe_index_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
