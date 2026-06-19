from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    """
    Schema for creating a new user.
    Called by WhatsApp Gateway after onboarding conversation completes.
    Only phone is required. Everything else is optional at creation time.
    """
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[List[str]] = []
    experience_level: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    availability: Optional[str] = "actively_looking"
    job_type_preference: Optional[List[str]] = []
    opt_in_status: Optional[bool] = True
    onboarding_state: Optional[str] = "IDLE"

    @field_validator("phone")
    @classmethod
    def phone_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Phone number cannot be empty")
        return v.strip()

    @field_validator("experience_level")
    @classmethod
    def validate_experience_level(cls, v):
        if v is not None:
            allowed = ["junior", "mid", "senior", "lead"]
            if v not in allowed:
                raise ValueError(f"experience_level must be one of: {allowed}")
        return v

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v):
        if v is not None:
            allowed = ["actively_looking", "open", "not_looking"]
            if v not in allowed:
                raise ValueError(f"availability must be one of: {allowed}")
        return v


class UserUpdate(BaseModel):
    """
    Schema for updating an existing user profile.
    All fields are optional — only provided fields get updated.
    Called by WhatsApp Gateway when user updates profile via menu.
    Also called by Matching Service to update cv_s3_key and cv_version.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    availability: Optional[str] = None
    job_type_preference: Optional[List[str]] = None
    opt_in_status: Optional[bool] = None
    cv_s3_key: Optional[str] = None
    cv_version: Optional[int] = None
    onboarding_state: Optional[str] = None

    @field_validator("experience_level")
    @classmethod
    def validate_experience_level(cls, v):
        if v is not None:
            allowed = ["junior", "mid", "senior", "lead"]
            if v not in allowed:
                raise ValueError(f"experience_level must be one of: {allowed}")
        return v


class UserResponse(BaseModel):
    """
    Schema for returning user data in API responses.
    This is what the API sends back to callers.
    """
    phone: str
    name: Optional[str]
    email: Optional[str]
    skills: Optional[List[str]]
    experience_level: Optional[str]
    location: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    availability: Optional[str]
    job_type_preference: Optional[List[str]]
    opt_in_status: bool
    cv_s3_key: Optional[str]
    cv_version: Optional[int]
    onboarding_state: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class OptStatusResponse(BaseModel):
    """
    Simple response for opt-in / opt-out endpoints.
    """
    message: str
    phone: str
    opt_in_status: bool
