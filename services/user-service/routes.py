from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User
from schemas import UserCreate, UserUpdate, UserResponse, OptStatusResponse
from redis_client import set_opt_in_status, delete_opt_in_status
from auth import require_admin

router = APIRouter(prefix="/users", tags=["Users"])


# ─────────────────────────────────────────────
# CREATE USER
# ─────────────────────────────────────────────
@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new job seeker profile.

    Called by: WhatsApp Gateway after onboarding conversation completes.

    Steps:
    1. Check if phone number already exists
    2. If exists → return 400 error (cannot create duplicate)
    3. Create new User record in PostgreSQL
    4. Set opt_in status in Redis (default True)
    5. Return the created user profile
    """
    # Check if user already exists
    existing = db.query(User).filter(User.phone == user.phone).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User with phone {user.phone} already exists. Use PATCH to update."
        )

    # Create new user
    new_user = User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Cache opt_in status in Redis — non-critical, don't fail if Redis is down
    try:
        set_opt_in_status(new_user.phone, new_user.opt_in_status)
    except Exception as e:
        print(f"[WARN] Redis unavailable, opt-in not cached for {new_user.phone}: {e}")

    return new_user


# ─────────────────────────────────────────────
# GET USER BY PHONE
# ─────────────────────────────────────────────
@router.get("/{phone}", response_model=UserResponse)
def get_user(phone: str, db: Session = Depends(get_db)):
    """
    Get a user profile by phone number.

    Called by:
    - WhatsApp Gateway (to show current values before update)
    - Matching Service (to get profile after CV embedding)
    - Notification Service (to get name for notification message)

    Returns 404 if user not found.
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {phone} not found"
        )
    return user


# ─────────────────────────────────────────────
# UPDATE USER
# ─────────────────────────────────────────────
@router.patch("/{phone}", response_model=UserResponse)
def update_user(phone: str, updates: UserUpdate, db: Session = Depends(get_db)):
    """
    Update any field(s) in the user profile.
    Only fields that are provided get updated.
    Fields not included in the request body remain unchanged.

    Called by:
    - WhatsApp Gateway when user updates profile via menu
    - Matching Service to update cv_s3_key and cv_version after CV processing

    Example: PATCH /users/94771234567
    Body: {"skills": ["Python", "React", "AWS"]}
    Only skills gets updated. Everything else stays the same.
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {phone} not found"
        )

    # Only update fields that were actually provided
    update_data = updates.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # If opt_in_status was updated, sync Redis too
    if "opt_in_status" in update_data:
        set_opt_in_status(phone, user.opt_in_status)

    return user


# ─────────────────────────────────────────────
# DELETE USER (PDPA Compliance)
# ─────────────────────────────────────────────
@router.delete("/{phone}")
def delete_user(phone: str, db: Session = Depends(get_db)):
    """
    Permanently delete a user and all their data.

    Required for PDPA (Personal Data Protection Act) compliance.
    User can request this by sending DELETE to WhatsApp.

    Steps:
    1. Find the user
    2. Delete from PostgreSQL
    3. Remove opt_in key from Redis
    4. Return confirmation

    Note: CV files in S3 should also be deleted separately
    by calling File Service. That is handled by WhatsApp Gateway.
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {phone} not found"
        )

    db.delete(user)
    db.commit()

    # Remove from Redis cache
    delete_opt_in_status(phone)

    return {"message": f"User {phone} deleted successfully"}


# ─────────────────────────────────────────────
# OPT OUT
# ─────────────────────────────────────────────
@router.patch("/{phone}/opt-out", response_model=OptStatusResponse)
def opt_out(phone: str, db: Session = Depends(get_db)):
    """
    Stop sending job alert notifications to this user.

    Called by: WhatsApp Gateway when user sends STOP message.

    Steps:
    1. Set opt_in_status = False in PostgreSQL (permanent)
    2. Set opt_in:{phone} = "false" in Redis (fast cache)
    3. Return confirmation

    After this the Notification Service will skip this user
    when sending job match alerts.
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {phone} not found"
        )

    # Update PostgreSQL
    user.opt_in_status = False
    user.onboarding_state = "OPTED_OUT"
    db.commit()

    # Update Redis cache
    set_opt_in_status(phone, False)

    return OptStatusResponse(
        message="User successfully opted out of job alerts",
        phone=phone,
        opt_in_status=False
    )


# ─────────────────────────────────────────────
# OPT IN
# ─────────────────────────────────────────────
@router.patch("/{phone}/opt-in", response_model=OptStatusResponse)
def opt_in(phone: str, db: Session = Depends(get_db)):
    """
    Resume sending job alert notifications to this user.

    Called by: WhatsApp Gateway when user sends START message.

    Steps:
    1. Set opt_in_status = True in PostgreSQL (permanent)
    2. Set opt_in:{phone} = "true" in Redis (fast cache)
    3. Return confirmation

    After this the Notification Service will include this user
    when sending job match alerts.
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with phone {phone} not found"
        )

    # Update PostgreSQL
    user.opt_in_status = True
    user.onboarding_state = "ACTIVE"
    db.commit()

    # Update Redis cache
    set_opt_in_status(phone, True)

    return OptStatusResponse(
        message="User successfully opted in to job alerts",
        phone=phone,
        opt_in_status=True
    )


# ─────────────────────────────────────────────
# GET ALL USERS (Admin only — for debugging)
# ─────────────────────────────────────────────
@router.get("", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Get all users with pagination.
    Used by Admin Service for monitoring and debugging.
    In production this should be protected by admin RBAC.

    Query params:
    - skip: how many records to skip (default 0)
    - limit: how many to return (default 50, max recommended 100)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users
