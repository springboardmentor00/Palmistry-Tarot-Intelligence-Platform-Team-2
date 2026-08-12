from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db
from backend.app.models.sql_models import (
    User,
    UserProfile,
    TarotCard,
    PalmReading,
    TarotReading,
    TarotReadingCard,
    AIInterpretation,
    GuidanceScore,
    Recommendation,
    Notification,
)
from backend.app.schemas.pydantic_schemas import (
    UserProfileUpdate,
    UserProfileResponse,
    UserResponse,
    PalmReadingCreate,
    PalmReadingResponse,
    TarotCardResponse,
    TarotReadingCreate,
    TarotReadingResponse,
    AIInterpretationResponse,
    GuidanceScoreResponse,
    RecommendationResponse,
    NotificationResponse,
    AdminAnalyticsResponse,
    UserManageUpdate,
)
from backend.app.auth.auth import get_current_user, RoleChecker
from backend.app.services.palm_cv import palm_cv_service
from backend.app.services.ai_service import ai_interpretation_service
from backend.app.services.tarot_deck import TarotDeckService
from backend.app.services.scoring import GuidanceScoringService
from backend.app.services.recommendations import RecommendationEngine

router = APIRouter(prefix="", tags=["Core"])

admin_only = RoleChecker(["ADMINISTRATOR"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile/me", response_model=UserProfileResponse)
def update_my_profile(
    update_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    update_data = update_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Palm Readings
# ---------------------------------------------------------------------------

@router.post("/palm/analyze", response_model=PalmReadingResponse)
def analyze_palm(
    payload: PalmReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Run CV analysis
    try:
        cv_result = palm_cv_service.analyze_palm_image(payload.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Persist palm reading
    palm_reading = PalmReading(
        user_id=current_user.id,
        image_path=cv_result["image_path"],
        processed_image_path=cv_result["processed_image_path"],
        palm_shape=cv_result["palm_shape"],
        finger_structure=cv_result["finger_structure"],
        life_line_conf=cv_result["life_line_conf"],
        head_line_conf=cv_result["head_line_conf"],
        heart_line_conf=cv_result["heart_line_conf"],
        fate_line_conf=cv_result["fate_line_conf"],
        sun_line_conf=cv_result["sun_line_conf"],
        overall_conf=cv_result["overall_conf"],
    )
    db.add(palm_reading)
    db.commit()
    db.refresh(palm_reading)

    # 3. Generate AI interpretation
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    goals = profile.goals if profile and profile.goals else []
    ai_result = ai_interpretation_service.generate_palm_interpretation(
        user_name=current_user.full_name,
        goals=goals,
        palm_data=cv_result,
    )
    db.add(AIInterpretation(
        reading_type="palm",
        reading_id=palm_reading.id,
        summary=ai_result["summary"],
        detailed_insight=ai_result["detailed_insight"],
        safety_disclaimer=ai_result["safety_disclaimer"],
    ))

    # 4. Score the reading
    GuidanceScoringService.calculate_score(
        db=db,
        reading_type="palm",
        reading_id=palm_reading.id,
        palm_conf=cv_result["overall_conf"],
    )

    # 5. Generate recommendations
    RecommendationEngine.generate_recommendations(
        db=db,
        user_id=current_user.id,
        goals=goals,
        reading_context="palm",
    )

    db.commit()
    return palm_reading


@router.get("/palm/history", response_model=List[PalmReadingResponse])
def get_palm_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(PalmReading)
        .filter(PalmReading.user_id == current_user.id)
        .order_by(PalmReading.created_at.desc())
        .all()
    )


@router.get("/palm/{reading_id}", response_model=PalmReadingResponse)
def get_palm_reading(
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reading = (
        db.query(PalmReading)
        .filter(PalmReading.id == reading_id, PalmReading.user_id == current_user.id)
        .first()
    )
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Palm reading not found.")
    return reading


# ---------------------------------------------------------------------------
# Tarot
# ---------------------------------------------------------------------------

@router.get("/tarot/cards", response_model=List[TarotCardResponse])
def list_tarot_cards(db: Session = Depends(get_db)):
    return db.query(TarotCard).all()


@router.post("/tarot/reading", response_model=TarotReadingResponse)
def create_tarot_reading(
    payload: TarotReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Draw the spread
    try:
        drawn = TarotDeckService.draw_spread(db, payload.spread_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Persist the reading + drawn cards
    tarot_reading = TarotReading(
        user_id=current_user.id,
        spread_name=payload.spread_name,
        focus_intent=payload.focus_intent,
    )
    db.add(tarot_reading)
    db.commit()
    db.refresh(tarot_reading)

    for entry in drawn:
        db.add(TarotReadingCard(
            reading_id=tarot_reading.id,
            card_id=entry["card"].id,
            position_name=entry["position_name"],
            is_reversed=entry["is_reversed"],
        ))
    db.commit()
    db.refresh(tarot_reading)

    # 3. Generate AI interpretation
    ai_result = ai_interpretation_service.generate_tarot_interpretation(
        user_name=current_user.full_name,
        intent=payload.focus_intent or "General",
        cards_drawn=drawn,
    )
    db.add(AIInterpretation(
        reading_type="tarot",
        reading_id=tarot_reading.id,
        summary=ai_result["summary"],
        detailed_insight=ai_result["detailed_insight"],
        safety_disclaimer=ai_result["safety_disclaimer"],
    ))

    # 4. Score the reading
    major_count = sum(1 for entry in drawn if entry["card"].arcana == "Major")
    tarot_relevance = round((major_count / len(drawn)) * 100, 1) if drawn else 80.0
    GuidanceScoringService.calculate_score(
        db=db,
        reading_type="tarot",
        reading_id=tarot_reading.id,
        tarot_relevance=tarot_relevance,
    )

    # 5. Generate recommendations
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    goals = profile.goals if profile and profile.goals else []
    RecommendationEngine.generate_recommendations(
        db=db,
        user_id=current_user.id,
        goals=goals,
        reading_context="tarot",
    )

    db.commit()
    return tarot_reading


@router.get("/tarot/history", response_model=List[TarotReadingResponse])
def get_tarot_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(TarotReading)
        .filter(TarotReading.user_id == current_user.id)
        .order_by(TarotReading.created_at.desc())
        .all()
    )


@router.get("/tarot/{reading_id}", response_model=TarotReadingResponse)
def get_tarot_reading(
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reading = (
        db.query(TarotReading)
        .filter(TarotReading.id == reading_id, TarotReading.user_id == current_user.id)
        .first()
    )
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarot reading not found.")
    return reading


# ---------------------------------------------------------------------------
# AI Interpretation & Guidance Score (shared lookup for palm/tarot)
# ---------------------------------------------------------------------------

@router.get("/interpretation/{reading_type}/{reading_id}", response_model=AIInterpretationResponse)
def get_interpretation(
    reading_type: str,
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interpretation = (
        db.query(AIInterpretation)
        .filter(
            AIInterpretation.reading_type == reading_type,
            AIInterpretation.reading_id == reading_id,
        )
        .first()
    )
    if not interpretation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interpretation not found.")
    return interpretation


@router.get("/score/{reading_type}/{reading_id}", response_model=GuidanceScoreResponse)
def get_guidance_score(
    reading_type: str,
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score = (
        db.query(GuidanceScore)
        .filter(
            GuidanceScore.reading_type == reading_type,
            GuidanceScore.reading_id == reading_id,
        )
        .first()
    )
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guidance score not found.")
    return score


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )


@router.patch("/recommendations/{rec_id}/complete", response_model=RecommendationResponse)
def complete_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = (
        db.query(Recommendation)
        .filter(Recommendation.id == rec_id, Recommendation.user_id == current_user.id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    rec.is_completed = True
    db.commit()
    db.refresh(rec)
    return rec


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.patch("/notifications/{notif_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notif_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/admin/analytics", response_model=AdminAnalyticsResponse, dependencies=[Depends(admin_only)])
def get_admin_analytics(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    palm_count = db.query(PalmReading).count()
    tarot_count = db.query(TarotReading).count()
    total_readings = palm_count + tarot_count

    scores = db.query(GuidanceScore).all()
    avg_score = round(sum(s.final_score for s in scores) / len(scores), 1) if scores else 0.0

    return AdminAnalyticsResponse(
        total_users=total_users,
        active_users=active_users,
        total_readings=total_readings,
        palm_readings=palm_count,
        tarot_readings=tarot_count,
        avg_guidance_score=avg_score,
        api_response_time_ms=0,
    )


@router.get("/admin/users", response_model=List[UserResponse], dependencies=[Depends(admin_only)])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.patch("/admin/users/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_only)])
def manage_user(
    user_id: int,
    update_in: UserManageUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    update_data = update_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
