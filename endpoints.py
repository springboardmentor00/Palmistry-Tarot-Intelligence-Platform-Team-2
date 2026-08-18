import io
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import RoleChecker, get_current_user, require_roles
from backend.app.database.mongo import mongo_db
from backend.app.database.postgres import get_db
from backend.app.models.sql_models import (
    AIInterpretation,
    GuidanceScore,
    Notification,
    PalmReading,
    Recommendation,
    TarotCard,
    TarotReading,
    TarotReadingCard,
    User,
    UserProfile,
)
from backend.app.schemas.pydantic_schemas import (
    AdminAnalyticsResponse,
    NotificationResponse,
    PalmReadingCreate,
    PalmReadingResponse,
    RecommendationResponse,
    TarotCardResponse,
    TarotReadingCreate,
    TarotReadingResponse,
    UserManageUpdate,
    UserProfileUpdate,
    UserResponse,
)
from backend.app.services.ai_service import ai_interpretation_service
from backend.app.services.palm_cv import palm_cv_service
from backend.app.services.recommendations import RecommendationEngine
from backend.app.services.scoring import GuidanceScoringService
from backend.app.services.tarot_deck import TarotDeckService
from backend.app.utils.reporting import ReportGenerator

router = APIRouter(tags=["Business Operations"])


# --------------------------------------------------------------------------
# USER PROFILE & SETTINGS
# --------------------------------------------------------------------------
@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/users/me", response_model=UserResponse)
def update_me(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if profile_in.age_group is not None:
        profile.age_group = profile_in.age_group
    if profile_in.interests is not None:
        profile.interests = profile_in.interests
    if profile_in.goals is not None:
        profile.goals = profile_in.goals
    if profile_in.preferences is not None:
        profile.preferences = profile_in.preferences

    db.commit()
    db.refresh(current_user)
    return current_user


# --------------------------------------------------------------------------
# PALMISTRY ANALYSIS
# --------------------------------------------------------------------------
@router.post("/palm/analyze", response_model=PalmReadingResponse)
def analyze_palm(
    payload: PalmReadingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        cv_results = palm_cv_service.analyze_palm_image(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    db_palm = PalmReading(
        user_id=current_user.id,
        image_path=cv_results.get("image_path", ""),
        processed_image_path=cv_results.get("processed_image_path", ""),
        palm_shape=cv_results.get("palm_shape", "Unknown"),
        finger_structure=cv_results.get("finger_structure", "Unknown"),
        life_line_conf=cv_results.get("life_line_conf", 0.0),
        head_line_conf=cv_results.get("head_line_conf", 0.0),
        heart_line_conf=cv_results.get("heart_line_conf", 0.0),
        fate_line_conf=cv_results.get("fate_line_conf", 0.0),
        sun_line_conf=cv_results.get("sun_line_conf", 0.0),
        overall_conf=cv_results.get("overall_conf", 0.0),
    )
    db.add(db_palm)
    db.commit()
    db.refresh(db_palm)

    # Safely pull user goals
    goals_list = (
        current_user.profile.goals
        if current_user.profile and current_user.profile.goals
        else []
    )

    # AI interpretation synthesis
    ai_result = ai_interpretation_service.generate_palm_interpretation(
        current_user.full_name, goals_list, cv_results
    )

    # Mongo document logging
    try:
        mongo_coll = mongo_db.get_collection("reading_analysis_documents")
        mongo_coll.insert_one(
            {
                "reading_type": "palm",
                "reading_id": db_palm.id,
                "email": current_user.email,
                "ai_output": ai_result,
            }
        )
    except Exception:
        pass  # Non-blocking log insertion fallback

    # Save SQL AI record
    db_ai = AIInterpretation(
        reading_type="palm",
        reading_id=db_palm.id,
        summary=ai_result.get("summary", ""),
        detailed_insight=ai_result.get("detailed_insight", ""),
        safety_disclaimer=ai_result.get("safety_disclaimer", ""),
    )
    db.add(db_ai)

    # Guidance Scoring
    GuidanceScoringService.calculate_score(
        db,
        "palm",
        db_palm.id,
        palm_conf=db_palm.overall_conf,
        tarot_relevance=85.0,
        personality_alignment=90.0,
        user_context=85.0,
        reading_consistency=80.0,
    )

    # Recommendations & Notifications
    RecommendationEngine.generate_recommendations(
        db, current_user.id, goals_list, cv_results.get("palm_shape", "Square")
    )

    notif = Notification(
        user_id=current_user.id,
        title="Palm Analysis Completed",
        message="Landmarks identified and guidance score resolved.",
    )
    db.add(notif)
    db.commit()

    return db_palm


@router.get("/palm/readings", response_model=List[PalmReadingResponse])
def get_my_palm_readings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(PalmReading).filter(PalmReading.user_id == current_user.id).all()


# --------------------------------------------------------------------------
# TAROT READINGS
# --------------------------------------------------------------------------
@router.get("/tarot/cards", response_model=List[TarotCardResponse])
def get_tarot_deck(db: Session = Depends(get_db)):
    TarotDeckService.seed_tarot_deck(db)
    return db.query(TarotCard).all()


@router.post("/tarot/readings", response_model=TarotReadingResponse)
def perform_tarot_reading(
    payload: TarotReadingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    TarotDeckService.seed_tarot_deck(db)

    # Draw spread
    drawn = TarotDeckService.draw_spread(db, payload.spread_name)

    # Save base reading
    db_reading = TarotReading(
        user_id=current_user.id,
        spread_name=payload.spread_name,
        focus_intent=payload.focus_intent,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)

    drawn_cards_metadata = []
    for d in drawn:
        card_obj = d["card"]
        db_drawn_card = TarotReadingCard(
            reading_id=db_reading.id,
            card_id=card_obj.id,
            position_name=d["position_name"],
            is_reversed=d["is_reversed"],
        )
        db.add(db_drawn_card)
        drawn_cards_metadata.append(
            {
                "card_name": card_obj.name,
                "position": d["position_name"],
                "orientation": "reversed" if d["is_reversed"] else "upright",
            }
        )
    db.commit()
    db.refresh(db_reading)

    # AI synthesis
    ai_result = ai_interpretation_service.generate_tarot_interpretation(
        current_user.full_name, payload.focus_intent, drawn
    )

    try:
        mongo_coll = mongo_db.get_collection("reading_analysis_documents")
        mongo_coll.insert_one(
            {
                "reading_type": "tarot",
                "reading_id": db_reading.id,
                "email": current_user.email,
                "cards": drawn_cards_metadata,
                "ai_output": ai_result,
            }
        )
    except Exception:
        pass

    db_ai = AIInterpretation(
        reading_type="tarot",
        reading_id=db_reading.id,
        summary=ai_result.get("summary", ""),
        detailed_insight=ai_result.get("detailed_insight", ""),
        safety_disclaimer=ai_result.get("safety_disclaimer", ""),
    )
    db.add(db_ai)

    # Scoring & Recommendations
    GuidanceScoringService.calculate_score(
        db,
        "tarot",
        db_reading.id,
        palm_conf=80.0,
        tarot_relevance=95.0,
        personality_alignment=85.0,
        user_context=90.0,
        reading_consistency=85.0,
    )

    goals_list = (
        current_user.profile.goals
        if current_user.profile and current_user.profile.goals
        else []
    )
    RecommendationEngine.generate_recommendations(
        db, current_user.id, goals_list, payload.spread_name
    )

    notif = Notification(
        user_id=current_user.id,
        title="Tarot Drawing Synthesized",
        message=f"Created insight analysis for {payload.spread_name} layout.",
    )
    db.add(notif)
    db.commit()

    return db_reading


# --------------------------------------------------------------------------
# RECOMMENDATIONS & NOTIFICATIONS
# --------------------------------------------------------------------------
@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id)
        .all()
    )


@router.put(
    "/recommendations/{id}/complete", response_model=RecommendationResponse
)
def complete_recommendation(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == id, Recommendation.user_id == current_user.id
        )
        .first()
    )
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    rec.is_completed = True
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .all()
    )


@router.put("/notifications/{id}/read", response_model=NotificationResponse)
def read_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


# --------------------------------------------------------------------------
# REPORTS & EXPORTS
# --------------------------------------------------------------------------
@router.get("/reports/pdf/{reading_type}/{reading_id}")
def export_pdf(
    reading_type: str,
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    synthesis = ""
    focus = ""
    score = 80

    if reading_type == "palm":
        palm = (
            db.query(PalmReading)
            .filter(
                PalmReading.id == reading_id,
                PalmReading.user_id == current_user.id,
            )
            .first()
        )
        if not palm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
            )
        ai_res = (
            db.query(AIInterpretation)
            .filter(
                AIInterpretation.reading_type == "palm",
                AIInterpretation.reading_id == reading_id,
            )
            .first()
        )
        synthesis = ai_res.detailed_insight if ai_res else ""
        focus = palm.palm_shape or "General"
        score_rec = (
            db.query(GuidanceScore)
            .filter(
                GuidanceScore.reading_type == "palm",
                GuidanceScore.reading_id == reading_id,
            )
            .first()
        )
        score = int(score_rec.final_score) if score_rec else 80
    else:
        tarot = (
            db.query(TarotReading)
            .filter(
                TarotReading.id == reading_id,
                TarotReading.user_id == current_user.id,
            )
            .first()
        )
        if not tarot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
            )
        ai_res = (
            db.query(AIInterpretation)
            .filter(
                AIInterpretation.reading_type == "tarot",
                AIInterpretation.reading_id == reading_id,
            )
            .first()
        )
        synthesis = ai_res.detailed_insight if ai_res else ""
        focus = tarot.spread_name
        score_rec = (
            db.query(GuidanceScore)
            .filter(
                GuidanceScore.reading_type == "tarot",
                GuidanceScore.reading_id == reading_id,
            )
            .first()
        )
        score = int(score_rec.final_score) if score_rec else 80

    reading_data = {
        "id": f"{reading_type.upper()}-{reading_id}",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "type": f"{reading_type.capitalize()} Analysis",
        "focus": focus,
        "score": score,
        "synthesis": synthesis,
    }

    pdf_bytes = ReportGenerator.generate_pdf_report(reading_data)
    return Response(
        content=pdf_bytes.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=aetheria_report_{reading_id}.pdf"
        },
    )


@router.get("/reports/excel/{reading_type}/{reading_id}")
def export_excel(
    reading_type: str,
    reading_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    focus = "Palm" if reading_type == "palm" else "Tarot"
    score = 80

    if reading_type == "palm":
        palm = (
            db.query(PalmReading)
            .filter(
                PalmReading.id == reading_id,
                PalmReading.user_id == current_user.id,
            )
            .first()
        )
        if palm:
            focus = palm.palm_shape or "General Palm"
            score_rec = (
                db.query(GuidanceScore)
                .filter(
                    GuidanceScore.reading_type == "palm",
                    GuidanceScore.reading_id == reading_id,
                )
                .first()
            )
            if score_rec:
                score = int(score_rec.final_score)
    else:
        tarot = (
            db.query(TarotReading)
            .filter(
                TarotReading.id == reading_id,
                TarotReading.user_id == current_user.id,
            )
            .first()
        )
        if tarot:
            focus = tarot.spread_name
            score_rec = (
                db.query(GuidanceScore)
                .filter(
                    GuidanceScore.reading_type == "tarot",
                    GuidanceScore.reading_id == reading_id,
                )
                .first()
            )
            if score_rec:
                score = int(score_rec.final_score)

    reading_data = {
        "id": f"{reading_type.upper()}-{reading_id}",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "type": f"{reading_type.capitalize()} Analysis",
        "focus": focus,
        "score": score,
    }

    excel_bytes = ReportGenerator.generate_excel_report(reading_data)
    return Response(
        content=excel_bytes.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=aetheria_data_{reading_id}.xlsx"
        },
    )


# --------------------------------------------------------------------------
# SPECIALIST & PROFESSIONAL ENDPOINTS (RBAC PROTECTED)
# --------------------------------------------------------------------------
@router.get(
    "/reader/queue",
    dependencies=[Depends(RoleChecker(["TAROT_READER", "ADMINISTRATOR"]))],
)
def get_reader_queue(db: Session = Depends(get_db)):
    readings = (
        db.query(TarotReading)
        .order_by(TarotReading.created_at.desc())
        .limit(50)
        .all()
    )
    return {"queue_length": len(readings), "readings": readings}


@router.get(
    "/consultant/clients",
    dependencies=[Depends(RoleChecker(["SPIRITUAL_CONSULTANT", "ADMINISTRATOR"]))],
)
def get_consultant_clients(db: Session = Depends(get_db)):
    clients = db.query(User).filter(User.role == "USER").all()
    return {"total_clients": len(clients), "clients": clients}


# --------------------------------------------------------------------------
# ADMIN ENDPOINTS (RBAC PROTECTED)
# --------------------------------------------------------------------------
@router.get(
    "/admin/analytics",
    response_model=AdminAnalyticsResponse,
    dependencies=[Depends(RoleChecker(["ADMINISTRATOR"]))],
)
def get_admin_analytics(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    palm_count = db.query(PalmReading).count()
    tarot_count = db.query(TarotReading).count()

    return {
        "total_users": user_count,
        "active_users": user_count,
        "total_readings": palm_count + tarot_count,
        "palm_readings": palm_count,
        "tarot_readings": tarot_count,
        "avg_guidance_score": 78.5,
        "api_response_time_ms": 14,
    }


@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    dependencies=[Depends(RoleChecker(["ADMINISTRATOR"]))],
)
def list_admin_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.put(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(["ADMINISTRATOR"]))],
)
def update_user_status(
    user_id: int, payload: UserManageUpdate, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user
