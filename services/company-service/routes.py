import uuid
import httpx
import os
import boto3
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID", "ap-south-1_0qt4DZnx6")
COGNITO_REGION  = os.getenv("COGNITO_REGION",  "ap-south-1")

from database import get_db
from models import Company, Job, JobMatch
from schemas import (
    CompanyCreate, CompanyResponse,
    JobCreate, JobResponse,
    JobMatchResponse, CandidateProfile,
    AdminStats,
)
from sqs_publisher import publish_job_matched
from auth import require_admin, require_employer, get_token_payload

router = APIRouter()

MATCHING_SERVICE_URL = os.getenv("MATCHING_SERVICE_URL", "http://localhost:8004")
USER_SERVICE_URL     = os.getenv("USER_SERVICE_URL",     "http://localhost:8001")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _call_matching_service(job_id: str, title: str, skills: list, description: str) -> list:
    """Call matching service to find candidate phones for a job. Returns [] on failure."""
    try:
        resp = httpx.post(
            f"{MATCHING_SERVICE_URL}/match/job",
            json={
                "job_id":      job_id,
                "title":       title,
                "skills":      skills,
                "description": description or "",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("matched_phones", [])
    except Exception as e:
        print(f"[WARN] Matching service unavailable: {e}")
    return []


def _embed_job_in_pinecone(job_id: str, title: str, skills: list, description: str) -> None:
    """Store job vector in Pinecone for reverse candidate-to-job matching."""
    try:
        httpx.post(
            f"{MATCHING_SERVICE_URL}/embed/job",
            json={
                "job_id":      job_id,
                "title":       title,
                "skills":      skills,
                "description": description or "",
            },
            timeout=15,
        )
    except Exception as e:
        print(f"[WARN] Could not store job vector: {e}")


def _fetch_candidate_profile(phone: str) -> Optional[CandidateProfile]:
    """Fetch a single user profile from user service. Returns minimal profile on failure."""
    try:
        resp = httpx.get(f"{USER_SERVICE_URL}/users/{phone}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return CandidateProfile(
                phone=data["phone"],
                name=data.get("name"),
                skills=data.get("skills") or [],
                experience_level=data.get("experience_level"),
                location=data.get("location"),
                cv_s3_key=data.get("cv_s3_key"),
            )
    except Exception as e:
        print(f"[WARN] Could not fetch profile for {phone}: {e}")
    return CandidateProfile(phone=phone)


# ── Company endpoints ─────────────────────────────────────────────────────────

@router.post("/companies", response_model=CompanyResponse)
def create_or_get_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    """
    Idempotent company registration.
    If a company already exists for this Cognito user, return it.
    Otherwise create a new PENDING company.
    Called by the Employer Dashboard on first login.
    """
    if payload.cognito_user_id:
        existing = db.query(Company).filter(
            Company.cognito_user_id == payload.cognito_user_id
        ).first()
        if existing:
            return existing

    by_email = db.query(Company).filter(Company.email == payload.email).first()
    if by_email:
        # Backfill cognito_user_id if it was missing so future by-user lookups work
        if not by_email.cognito_user_id and payload.cognito_user_id:
            by_email.cognito_user_id = payload.cognito_user_id
            db.commit()
            db.refresh(by_email)
        return by_email

    company = Company(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        industry=payload.industry,
        cognito_user_id=payload.cognito_user_id,
        status="PENDING",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/companies/by-user/{cognito_user_id}", response_model=CompanyResponse)
def get_company_by_user(cognito_user_id: str, db: Session = Depends(get_db)):
    """Return the company registered for a given Cognito user sub."""
    company = db.query(Company).filter(Company.cognito_user_id == cognito_user_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="No company found for this user")
    return company


@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


# ── Job endpoints (employer) ──────────────────────────────────────────────────

@router.post("/companies/{company_id}/jobs", response_model=JobResponse)
def post_job(
    company_id: str,
    payload: JobCreate,
    db: Session = Depends(get_db),
    _payload: dict = Depends(require_employer),
):
    """
    Post a new job listing.
    Flow: create → embed vector → match candidates → SQS notification
    Only APPROVED companies may post jobs.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"Company is {company.status}. Only APPROVED companies can post jobs.",
        )

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        company_id=company_id,
        company_name=company.name,
        title=payload.title,
        location=payload.location,
        job_type=payload.job_type,
        salary=payload.salary,
        description=payload.description,
        skills=payload.skills or [],
        deadline=payload.deadline,
        status="Active",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Store job vector for reverse matching (best-effort)
    _embed_job_in_pinecone(
        job_id=job_id,
        title=payload.title,
        skills=payload.skills or [],
        description=payload.description or "",
    )

    # Find matching candidates
    matched_phones = _call_matching_service(
        job_id=job_id,
        title=payload.title,
        skills=payload.skills or [],
        description=payload.description or "",
    )

    if matched_phones:
        job.applications = len(matched_phones)
        db.add(JobMatch(job_id=job_id, matched_phones=matched_phones))
        db.commit()
        db.refresh(job)

        publish_job_matched(
            job_id=job_id,
            job_title=payload.title,
            company_name=company.name,
            location=payload.location or "",
            job_type=payload.job_type or "",
            salary=payload.salary or "",
            matched_phones=matched_phones,
        )

    return job


@router.get("/companies/{company_id}/jobs", response_model=List[JobResponse])
def get_company_jobs(company_id: str, db: Session = Depends(get_db)):
    """Return all jobs posted by a company, newest first."""
    return (
        db.query(Job)
        .filter(Job.company_id == company_id)
        .order_by(Job.posted_at.desc())
        .all()
    )


@router.patch("/jobs/{job_id}/status", response_model=JobResponse)
def toggle_job_status(job_id: str, db: Session = Depends(get_db)):
    """Toggle a job between Active and Closed."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "Closed" if job.status == "Active" else "Active"
    db.commit()
    db.refresh(job)
    return job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.query(JobMatch).filter(JobMatch.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    try:
        httpx.delete(f"{MATCHING_SERVICE_URL}/embed/job/{job_id}", timeout=10)
    except Exception as e:
        print(f"[WARN] Could not delete job vector from Pinecone: {e}")
    return {"message": f"Job {job_id} deleted"}


@router.get("/jobs/{job_id}/matches", response_model=JobMatchResponse)
def get_job_matches(job_id: str, db: Session = Depends(get_db)):
    """Return matched candidates enriched with profiles from user service."""
    match = db.query(JobMatch).filter(JobMatch.job_id == job_id).first()
    if not match:
        return JobMatchResponse(job_id=job_id, matched_phones=[], total_matches=0, candidates=[])

    phones     = match.matched_phones or []
    candidates = [_fetch_candidate_profile(p) for p in phones]

    return JobMatchResponse(
        job_id=job_id,
        matched_phones=phones,
        total_matches=len(phones),
        candidates=candidates,
    )


# ── Reverse matching — called by Matching Service ─────────────────────────────

from pydantic import BaseModel as _BaseModel

class _ApplicantAdd(_BaseModel):
    phone: str


@router.post("/jobs/{job_id}/applicants")
def add_applicant(job_id: str, payload: _ApplicantAdd, db: Session = Depends(get_db)):
    """
    Add a reverse-matched candidate to a job's applicant list.
    Called by Matching Service when a new CV matches an active job.
    Idempotent — won't add duplicates.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.status == "Active").first()
    if not job:
        return {"status": "skipped", "reason": "job not found or closed"}

    match = db.query(JobMatch).filter(JobMatch.job_id == job_id).first()
    if not match:
        match = JobMatch(job_id=job_id, matched_phones=[payload.phone])
        db.add(match)
    elif payload.phone in (match.matched_phones or []):
        return {"status": "already_matched"}
    else:
        match.matched_phones = (match.matched_phones or []) + [payload.phone]

    job.applications = len(match.matched_phones)
    db.commit()
    return {"status": "added", "job_id": job_id, "phone": payload.phone}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/companies", response_model=List[CompanyResponse])
def admin_list_companies(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """List all companies with optional status filter."""
    q = db.query(Company)
    if status:
        q = q.filter(Company.status == status)
    return q.order_by(Company.registered_at.desc()).offset(skip).limit(limit).all()


@router.patch("/admin/companies/{company_id}/approve", response_model=CompanyResponse)
def approve_company(
    company_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = "APPROVED"
    db.commit()
    db.refresh(company)
    return company


@router.patch("/admin/companies/{company_id}/reject", response_model=CompanyResponse)
def reject_company(
    company_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = "REJECTED"
    db.commit()
    db.refresh(company)
    return company


@router.patch("/admin/companies/{company_id}/activate", response_model=CompanyResponse)
def activate_company(
    company_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Approve a self-registered company AND add the employer to the
    quickjobs-employers Cognito group so they can log in immediately.
    Returns 503 if the Cognito group assignment fails so the admin is informed.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        cognito = boto3.client("cognito-idp", region_name=COGNITO_REGION)

        # Ensure the group exists — create it if missing
        try:
            cognito.create_group(
                UserPoolId=COGNITO_POOL_ID,
                GroupName="quickjobs-employers",
                Description="Approved employers who can post jobs",
            )
            print("[INFO] Created Cognito group quickjobs-employers")
        except cognito.exceptions.GroupExistsException:
            pass  # group already exists, that's fine

        cognito.admin_add_user_to_group(
            UserPoolId=COGNITO_POOL_ID,
            Username=company.email,
            GroupName="quickjobs-employers",
        )
        print(f"[INFO] Added {company.email} to quickjobs-employers Cognito group")
    except Exception as e:
        print(f"[ERROR] Cognito group assignment failed for {company.email}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Cognito error: {str(e)}. Check AWS IAM permissions (cognito-idp:CreateGroup, cognito-idp:AdminAddUserToGroup) and that the user pool ID is correct.",
        )

    company.status = "APPROVED"
    db.commit()
    db.refresh(company)
    return company


@router.patch("/admin/companies/{company_id}/suspend", response_model=CompanyResponse)
def suspend_company(
    company_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Suspend a company. Their jobs remain but they cannot post new listings."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = "SUSPENDED"
    db.commit()
    db.refresh(company)
    return company


@router.get("/admin/jobs", response_model=List[JobResponse])
def admin_list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """List all jobs across all companies."""
    return (
        db.query(Job)
        .order_by(Job.posted_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.get("/admin/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Platform-wide KPIs for the admin panel overview."""
    all_companies = db.query(Company).all()
    all_jobs      = db.query(Job).all()
    total_matches = db.query(JobMatch).count()

    return AdminStats(
        total_companies=len(all_companies),
        pending_approvals=sum(1 for c in all_companies if c.status == "PENDING"),
        approved_companies=sum(1 for c in all_companies if c.status == "APPROVED"),
        total_jobs=len(all_jobs),
        active_jobs=sum(1 for j in all_jobs if j.status == "Active"),
        total_matches=total_matches,
    )
