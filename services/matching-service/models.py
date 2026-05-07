from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MatchedPair(Base):
    """
    Tracks which candidates have already been notified for a job.
    Prevents the same candidate from receiving duplicate notifications.

    Example:
        job_id="job_123", seeker_phone="94771234567"
        → this pair is stored after notification is sent
        → if matching runs again, this pair is skipped
    """
    __tablename__ = "matched_pairs"

    job_id = Column(String, primary_key=True, nullable=False)
    seeker_phone = Column(String, primary_key=True, nullable=False)
    matched_at = Column(DateTime, server_default=func.now())


class JobPosting(Base):
    """
    Local copy of job postings received via SQS.
    Stored here so the matching service can reference job details
    without calling the company service on every match.
    """
    __tablename__ = "job_postings"

    job_id = Column(String, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    company_id = Column(String, nullable=False)
    skills_required = Column(String, nullable=False)  # stored as comma-separated
    experience_level = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, default="active")  # active / closed
    created_at = Column(DateTime, server_default=func.now())