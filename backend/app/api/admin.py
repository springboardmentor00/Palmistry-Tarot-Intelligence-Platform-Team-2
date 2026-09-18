from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.auth import require_roles
from backend.app.database.postgres import get_db
from backend.app.models.sql_models import GuidanceScore, PalmReading, TarotReading, User
from backend.app.schemas.pydantic_schemas import AdminAnalyticsResponse, UserManageUpdate, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin Management"], dependencies=[Depends(require_roles(["ADMINISTRATOR"]))])


@router.get("/users", response_model=List[UserResponse])
def list_all_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_status(user_id: int, payload: UserManageUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        role = payload.role.upper()
        if role not in {"USER", "TAROT_READER", "SPIRITUAL_CONSULTANT", "ADMINISTRATOR"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
    if payload.is_active is not None: user.is_active = payload.is_active
    db.commit(); db.refresh(user); return user


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_admin_analytics(db: Session = Depends(get_db)):
    users = db.query(User).count()
    active = db.query(User).filter(User.is_active.is_(True)).count()
    palms = db.query(PalmReading).count()
    tarot = db.query(TarotReading).count()
    avg = db.query(func.avg(GuidanceScore.final_score)).scalar()
    return AdminAnalyticsResponse(total_users=users, active_users=active, total_readings=palms + tarot, palm_readings=palms, tarot_readings=tarot, avg_guidance_score=round(float(avg), 2) if avg is not None else None, api_response_time_ms=None)
