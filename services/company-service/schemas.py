from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CompanyCreate(BaseModel):
    name:            str
    email:           str
    industry:        Optional[str]  = None
    cognito_user_id: Optional[str]  = None


class CompanyResponse(BaseModel):
    id:              str
    name:            str
    email:           str
    industry:        Optional[str]
    status:          str
    registered_at:   datetime
    cognito_user_id: Optional[str] = None

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    title:       str
    location:    Optional[str]       = None
    job_type:    Optional[str]       = "Full-time"
    salary:      Optional[str]       = None
    description: Optional[str]       = None
    skills:      Optional[List[str]] = []
    deadline:    Optional[str]       = None


class JobResponse(BaseModel):
    id:           str
    company_id:   str
    company_name: str
    title:        str
    location:     Optional[str]
    job_type:     Optional[str]
    salary:       Optional[str]
    description:  Optional[str]
    skills:       Optional[List[str]]
    deadline:     Optional[str]
    status:       str
    applications: int
    posted_at:    datetime

    class Config:
        from_attributes = True


class CandidateProfile(BaseModel):
    phone:            str
    name:             Optional[str]      = None
    skills:           Optional[List[str]] = []
    experience_level: Optional[str]      = None
    location:         Optional[str]      = None
    cv_s3_key:        Optional[str]      = None


class JobMatchResponse(BaseModel):
    job_id:          str
    matched_phones:  List[str]
    total_matches:   int
    candidates:      List[CandidateProfile] = []


class AdminStats(BaseModel):
    total_companies:    int
    pending_approvals:  int
    approved_companies: int
    total_jobs:         int
    active_jobs:        int
    total_matches:      int
