from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.profile_schema import (
    ProfileResponse,
    ProfileUpdate
)
from app.database import get_db

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)


@router.get("/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return ProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email
    )


@router.put("/{user_id}")
def update_profile(
    user_id: int,
    profile: ProfileUpdate,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.name = profile.name

    db.commit()
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "name": user.name
    }