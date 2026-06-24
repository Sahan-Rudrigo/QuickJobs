from sqlalchemy import Column, String, Integer, DateTime, Text, ARRAY
from sqlalchemy.sql import func
from database import Base


class Company(Base):
    __tablename__ = "companies"

    id              = Column(String, primary_key=True)           # UUID
    name            = Column(String, nullable=False)
    email           = Column(String, nullable=False, unique=True)
    industry        = Column(String, nullable=True)
    cognito_user_id = Column(String, nullable=True, unique=True)  # Cognito sub
    status          = Column(String, default="PENDING")           # PENDING | APPROVED | REJECTED | SUSPENDED
    registered_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id           = Column(String, primary_key=True)      # UUID
    company_id   = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    title        = Column(String, nullable=False)
    location     = Column(String, nullable=True)
    job_type     = Column(String, default="Full-time")
    salary       = Column(String, nullable=True)
    description  = Column(Text, nullable=True)
    skills       = Column(ARRAY(String), default=[])
    deadline     = Column(String, nullable=True)
    status       = Column(String, default="Active")       # Active | Closed
    applications = Column(Integer, default=0)
    posted_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())


class JobMatch(Base):
    __tablename__ = "job_matches"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    job_id         = Column(String, nullable=False, index=True)
    matched_phones = Column(ARRAY(String), default=[])
    matched_at     = Column(DateTime(timezone=True), server_default=func.now())
