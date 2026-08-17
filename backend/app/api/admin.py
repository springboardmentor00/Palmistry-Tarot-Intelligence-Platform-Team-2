from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db
from backend.app.models.sql_models import User, PalmReading, TarotReading, Recommendation
from backend.app.schemas.pydantic_schemas import UserResponse, UserManageUpdate
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.utils.pdf_generator import generate_user_report

router = APIRouter(prefix="/admin", tags=["Admin"])

require_admin = RoleChecker(["ADMINISTRATOR"])

VALID_ROLES = {"USER", "TAROT_READER", "SPIRITUAL_CONSULTANT", "ADMINISTRATOR"}


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all users with optional filtering, searching, and pagination."""
    query = db.query(User)

    if role:
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {sorted(VALID_ROLES)}")
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if search:
        like = f"%{search}%"
        query = query.filter((User.full_name.ilike(like)) | (User.email.ilike(like)))

    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get a single user's full profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    update_in: UserManageUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update a user's role and/or active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.id == admin.id and update_in.is_active is False:
        raise HTTPException(status_code=400, detail="Administrators cannot deactivate their own account.")

    if update_in.role is not None:
        if update_in.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {sorted(VALID_ROLES)}")
        user.role = update_in.role

    if update_in.is_active is not None:
        user.is_active = update_in.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Permanently delete a user and their related data (cascades)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Administrators cannot delete their own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    db.delete(user)
    db.commit()
    return None


@router.get("/users/{user_id}/summary")
def user_activity_summary(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Quick counts of a user's activity, useful for the admin dashboard."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    palm_count = db.query(PalmReading).filter(PalmReading.user_id == user_id).count()
    tarot_count = db.query(TarotReading).filter(TarotReading.user_id == user_id).count()
    recommendation_count = db.query(Recommendation).filter(Recommendation.user_id == user_id).count()

    return {
        "user_id": user_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "palm_readings": palm_count,
        "tarot_readings": tarot_count,
        "recommendations": recommendation_count,
    }


@router.get("/users/{user_id}/report")
def download_user_report(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Generate and download a PDF report of a user's readings and recommendations."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    file_path = generate_user_report(db, user)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"aetheria_report_user_{user_id}.pdf",
    )