import uuid
import httpx
import os
import boto3
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional

COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID", "ap-south-1_0qt4DZnx6")
COGNITO_REGION  = os.getenv("COGNITO_REGION",  "ap-south-1")

from database import get_db
from models import Company, Job, JobApplication
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


def _create_notified_applications(db: Session, job_id: str, phones: list) -> list:
    """
    Insert a NOTIFIED JobApplication row for each phone that doesn't already
    have one for this job. Returns only the phones that were newly inserted —
    dedups repeat forward/reverse matches for the same (job_id, phone) pair.
    """
    existing = {
        row.phone for row in
        db.query(JobApplication.phone).filter(JobApplication.job_id == job_id).all()
    }
    new_phones = [p for p in phones if p not in existing]
    for phone in new_phones:
        db.add(JobApplication(job_id=job_id, phone=phone, status="NOTIFIED"))
    if new_phones:
        db.commit()
    return new_phones


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
        newly_notified = _create_notified_applications(db, job_id, matched_phones)
        if newly_notified:
            publish_job_matched(
                job_id=job_id,
                job_title=payload.title,
                company_name=company.name,
                location=payload.location or "",
                job_type=payload.job_type or "",
                salary=payload.salary or "",
                description=payload.description or "",
                matched_phones=newly_notified,
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
    db.query(JobApplication).filter(JobApplication.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    try:
        httpx.delete(f"{MATCHING_SERVICE_URL}/embed/job/{job_id}", timeout=10)
    except Exception as e:
        print(f"[WARN] Could not delete job vector from Pinecone: {e}")
    return {"message": f"Job {job_id} deleted"}


@router.get("/jobs/{job_id}/matches", response_model=JobMatchResponse)
def get_job_matches(job_id: str, db: Session = Depends(get_db)):
    """
    Return candidates enriched with profiles from user service.
    Only candidates who explicitly APPLIED are returned — a candidate merely
    notified of the match is not visible to the employer until they consent.
    """
    rows = (
        db.query(JobApplication)
        .filter(JobApplication.job_id == job_id, JobApplication.status == "APPLIED")
        .all()
    )
    phones     = [r.phone for r in rows]
    candidates = [_fetch_candidate_profile(p) for p in phones]

    return JobMatchResponse(
        job_id=job_id,
        matched_phones=phones,
        total_matches=len(phones),
        candidates=candidates,
    )


# ── Reverse matching — called by Matching Service ─────────────────────────────

from pydantic import BaseModel as _BaseModel

class _NotifyMatchRequest(_BaseModel):
    phones: List[str]


@router.post("/jobs/{job_id}/notify-match")
def notify_match(job_id: str, payload: _NotifyMatchRequest, db: Session = Depends(get_db)):
    """
    Record reverse-matched candidates as NOTIFIED and trigger the same
    job-matched SQS publish used by forward matching, so they get a WhatsApp
    offer and must APPLY before appearing to the employer.
    Called by Matching Service when a new CV matches an active job.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.status == "Active").first()
    if not job:
        return {"status": "skipped", "reason": "job not found or closed"}

    newly_notified = _create_notified_applications(db, job_id, payload.phones)
    if newly_notified:
        publish_job_matched(
            job_id=job_id,
            job_title=job.title,
            company_name=job.company_name,
            location=job.location or "",
            job_type=job.job_type or "",
            salary=job.salary or "",
            description=job.description or "",
            matched_phones=newly_notified,
        )
    return {"status": "ok", "job_id": job_id, "notified": newly_notified}


class _DecisionRequest(_BaseModel):
    decision: str  # "APPLY" | "SKIP"


@router.patch("/jobs/{job_id}/applicants/{phone}")
def decide_application(job_id: str, phone: str, payload: _DecisionRequest, db: Session = Depends(get_db)):
    """
    Record a candidate's APPLY/SKIP decision for a job they were notified about.
    Also used for "reapply" — a REJECTED row can transition back to APPLIED.
    Called by WhatsApp Gateway when the candidate replies APPLY or SKIP.
    """
    app_row = db.query(JobApplication).filter_by(job_id=job_id, phone=phone).first()
    job     = db.query(Job).filter(Job.id == job_id).first()
    if not app_row or not job:
        raise HTTPException(status_code=404, detail="Application not found")

    target = "APPLIED" if payload.decision.upper() == "APPLY" else "REJECTED"

    # NOTIFIED -> APPLIED/REJECTED (first response), or REJECTED -> APPLIED
    # (reapply). Any other transition is an idempotent no-op.
    if app_row.status == "NOTIFIED" or (app_row.status == "REJECTED" and target == "APPLIED"):
        app_row.status       = target
        app_row.responded_at = func.now()
        db.flush()  # session has autoflush=False — the count below must see this pending status change
        job.applications = (
            db.query(JobApplication)
            .filter_by(job_id=job_id, status="APPLIED")
            .count()
        )
        db.commit()

    return {
        "status":       app_row.status,
        "job_id":       job_id,
        "phone":        phone,
        "job_title":    job.title,
        "company_name": job.company_name,
    }


@router.get("/candidates/{phone}/applications")
def get_candidate_applications(phone: str, status: str, db: Session = Depends(get_db)):
    """
    Return a candidate's own jobs filtered by status (APPLIED or REJECTED).
    Called by WhatsApp Gateway for the "My Applications"/"Rejected Jobs" menu.
    """
    rows = (
        db.query(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .filter(JobApplication.phone == phone, JobApplication.status == status.upper())
        .order_by(JobApplication.responded_at.desc())
        .all()
    )
    return [
        {
            "job_id":       job.id,
            "title":        job.title,
            "company_name": job.company_name,
            "location":     job.location,
            "salary":       job.salary,
        }
        for _app, job in rows
    ]


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
    total_matches = db.query(JobApplication).count()

    return AdminStats(
        total_companies=len(all_companies),
        pending_approvals=sum(1 for c in all_companies if c.status == "PENDING"),
        approved_companies=sum(1 for c in all_companies if c.status == "APPROVED"),
        total_jobs=len(all_jobs),
        active_jobs=sum(1 for j in all_jobs if j.status == "Active"),
        total_matches=total_matches,
    )
