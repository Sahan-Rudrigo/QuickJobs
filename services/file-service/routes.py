import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import CVRecord
from schemas import CVUploadResponse, CVRecordResponse
from extractor import extract_text
from s3_client import upload_cv, delete_cv, get_presigned_url, MAX_CV_VERSIONS
from sqs_publisher import publish_cv_uploaded

router = APIRouter(prefix="/cv", tags=["CV"])


@router.post("/upload/{phone}", response_model=CVUploadResponse)
async def upload_cv_file(
    phone: str,
    file: UploadFile = File(...),
    skills: Optional[str] = Form(default="[]"),
    experience: Optional[str] = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    Receive a CV file from the WhatsApp Gateway.
    Steps:
    1. Extract text from PDF / DOCX
    2. Upload file to S3 with versioning
    3. Enforce max 3 versions — delete oldest if exceeded
    4. Save record to PostgreSQL
    5. Publish cv.uploaded event to SQS → triggers Matching Service
    """
    file_bytes = await file.read()
    mime_type  = file.content_type or "application/pdf"
    filename   = file.filename or "cv.pdf"

    # ── 1. Extract text ──────────────────────────────────────────
    full_text, file_type = extract_text(file_bytes, mime_type)
    if not full_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this file. Please upload a readable PDF or Word document."
        )

    # ── 2. Calculate next version number ─────────────────────────
    existing = (
        db.query(CVRecord)
        .filter(CVRecord.phone == phone)
        .order_by(CVRecord.version.asc())
        .all()
    )
    next_version = (existing[-1].version + 1) if existing else 1

    # ── 3. Upload to S3 ──────────────────────────────────────────
    s3_key = upload_cv(phone, next_version, filename, file_bytes, mime_type)

    # ── 4. Save to DB ────────────────────────────────────────────
    record = CVRecord(
        phone=phone,
        s3_key=s3_key,
        version=next_version,
        file_name=filename,
        file_type=file_type,
        text_length=len(full_text),
    )
    db.add(record)

    # ── 5. Enforce max 3 versions ────────────────────────────────
    if len(existing) >= MAX_CV_VERSIONS:
        oldest = existing[0]
        delete_cv(oldest.s3_key)
        db.delete(oldest)

    db.commit()

    # ── 6. Parse skills and publish SQS event ────────────────────
    try:
        skills_list: List[str] = json.loads(skills) if skills else []
    except (json.JSONDecodeError, TypeError):
        skills_list = []

    publish_cv_uploaded(
        phone=phone,
        s3_key=s3_key,
        cv_version=next_version,
        skills=skills_list,
        experience=experience or "",
        full_text=full_text,
    )

    return CVUploadResponse(
        status="success",
        phone=phone,
        s3_key=s3_key,
        version=next_version,
        text_length=len(full_text),
        message=f"CV v{next_version} uploaded and queued for matching.",
    )


@router.get("/{phone}", response_model=List[CVRecordResponse])
def get_cv_records(phone: str, db: Session = Depends(get_db)):
    """
    Return all CV versions for a job seeker.
    Most recent version is last in the list.
    """
    records = (
        db.query(CVRecord)
        .filter(CVRecord.phone == phone)
        .order_by(CVRecord.version.asc())
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail=f"No CV found for {phone}")
    return records


@router.get("/{phone}/latest/download")
def get_cv_download_url(phone: str, db: Session = Depends(get_db)):
    """Return a pre-signed S3 URL to download the latest CV (valid 1 hour)."""
    latest = (
        db.query(CVRecord)
        .filter(CVRecord.phone == phone)
        .order_by(CVRecord.version.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail=f"No CV found for {phone}")

    url = get_presigned_url(latest.s3_key)
    return {"phone": phone, "version": latest.version, "download_url": url}


@router.delete("/{phone}")
def delete_all_cv_records(phone: str, db: Session = Depends(get_db)):
    """
    Delete all CV versions for a phone number from S3 and the database.
    Called by the WhatsApp Gateway during PDPA right-to-erasure flow.
    """
    records = (
        db.query(CVRecord)
        .filter(CVRecord.phone == phone)
        .all()
    )
    deleted = 0
    for record in records:
        try:
            delete_cv(record.s3_key)
        except Exception as e:
            print(f"[WARN] Could not delete S3 object {record.s3_key}: {e}")
        db.delete(record)
        deleted += 1

    db.commit()
    return {"phone": phone, "deleted_versions": deleted, "message": f"Deleted {deleted} CV version(s)"}
