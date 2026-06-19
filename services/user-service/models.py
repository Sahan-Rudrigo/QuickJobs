from sqlalchemy import Column, String, Boolean, Integer, DateTime, ARRAY
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """
    User table in PostgreSQL.
    Stores all job seeker profile information.
    Primary key is phone number (WhatsApp number).
    """
    __tablename__ = "users"

    # Primary identifier — WhatsApp phone number
    # Format: country code + number e.g. 94771234567
    phone = Column(String, primary_key=True, index=True)

    # Basic personal info collected during WhatsApp onboarding
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # Professional info
    # skills is an array of strings e.g. ["Python", "React", "SQL"]
    skills = Column(ARRAY(String), default=[])

    # One of: junior, mid, senior, lead
    experience_level = Column(String, nullable=True)

    # City or region e.g. "Colombo" or "Kandy"
    location = Column(String, nullable=True)

    # Salary expectation range in LKR per month
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)

    # One of: actively_looking, open, not_looking
    availability = Column(String, default="actively_looking")

    # Job type preferences e.g. ["full-time", "remote"]
    job_type_preference = Column(ARRAY(String), default=[])

    # Controls whether this user receives WhatsApp job alerts
    # True  = send alerts (default)
    # False = user sent STOP, do not send alerts
    opt_in_status = Column(Boolean, default=True)

    # CV file info — points to the file stored in S3
    # e.g. "cvs/94771234567/v2/cv.pdf"
    cv_s3_key = Column(String, nullable=True)

    # Tracks which version of CV is currently active
    # Increments each time user uploads a new CV
    cv_version = Column(Integer, default=0)

    # Tracks where user is in the WhatsApp onboarding conversation
    # States: IDLE, AWAITING_NAME, AWAITING_SKILLS, AWAITING_EXPERIENCE,
    #         AWAITING_LOCATION, AWAITING_SALARY, AWAITING_CV,
    #         ACTIVE, OPTED_OUT
    onboarding_state = Column(String, default="IDLE")

    # Automatic timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
