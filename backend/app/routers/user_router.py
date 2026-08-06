from fastapi import APIRouter, Depends

from app.core.dependencies import (
    get_current_user,
    require_role
)

from app.schemas.user_schema import ProfileUpdate

router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@router.get("/profile")
def profile(
    current_user=Depends(get_current_user)
):
    return current_user


@router.put("/profile")
def update_profile(
    profile: ProfileUpdate,
    current_user=Depends(get_current_user)
):
    current_user["name"] = profile.name

    return {
        "message": "Profile updated successfully",
        "user": current_user
    }


@router.get("/dashboard")
def dashboard(
    current_user=Depends(get_current_user)
):
    return {
        "message": "Welcome!",
        "user": current_user
    }


@router.get("/tarot-reader")
def tarot_dashboard(
    current_user=Depends(
        require_role("Tarot Reader")
    )
):
    return {
        "message": "Welcome Tarot Reader"
    }


@router.get("/spiritual-consultant")
def consultant_dashboard(
    current_user=Depends(
        require_role("Spiritual Consultant")
    )
):
    return {
        "message": "Welcome Spiritual Consultant"
    }


@router.get("/admin")
def admin_dashboard(
    current_user=Depends(
        require_role("Administrator")
    )
):
    return {
        "message": "Welcome Administrator"
    }