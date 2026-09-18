import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.auth import RoleChecker, get_current_user
from backend.app.database.postgres import get_db
from backend.app.models.sql_models import (
    AIInterpretation, GuidanceScore, Notification, PalmReading, Recommendation,
    TarotCard, TarotReading, TarotReadingCard, User, UserProfile,
)
from backend.app.schemas.pydantic_schemas import (
    CombinedMasterReportResponse, CombinedReadingCreate, ComprehensiveInsightResponse,
    NotificationResponse, PalmReadingCreate, PalmReadingResponse, RecommendationResponse,
    TarotCardResponse, TarotReadingCreate, TarotReadingResponse, UserProfileUpdate, UserResponse,
)
from backend.app.services.ai_service import ai_interpretation_service
from backend.app.services.life_trend import LifeTrendService
from backend.app.services.personality import PersonalityService
from backend.app.services.palm_cv import palm_cv_service
from backend.app.services.recommendations import RecommendationEngine
from backend.app.services.scoring import GuidanceScoringService
from backend.app.services.tarot_deck import TarotDeckService
from backend.app.utils.reporting import ReportGenerator

router = APIRouter(tags=["Business Operations"])


def _score(db: Session, reading_type: str, reading_id: int):
    return db.query(GuidanceScore).filter(GuidanceScore.reading_type == reading_type, GuidanceScore.reading_id == reading_id).order_by(GuidanceScore.created_at.desc()).first()


def _ai(db: Session, reading_type: str, reading_id: int):
    return db.query(AIInterpretation).filter(AIInterpretation.reading_type == reading_type, AIInterpretation.reading_id == reading_id).order_by(AIInterpretation.created_at.desc()).first()


def _palm_response(db, palm):
    ai = _ai(db, "palm", palm.id); score = _score(db, "palm", palm.id)
    data = PalmReadingResponse.model_validate(palm).model_dump()
    if ai: data.update(summary=ai.summary, detailed_insight=ai.detailed_insight, safety_disclaimer=ai.safety_disclaimer)
    if score: data["guidance_score"] = score.final_score
    return data


def _tarot_response(db, reading):
    ai = _ai(db, "tarot", reading.id); score = _score(db, "tarot", reading.id)
    data = TarotReadingResponse.model_validate(reading).model_dump()
    if ai: data.update(summary=ai.summary, detailed_insight=ai.detailed_insight, safety_disclaimer=ai.safety_disclaimer)
    if score: data["guidance_score"] = score.final_score
    return data


@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/users/me", response_model=UserResponse)
def update_me(profile_in: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = current_user.profile or UserProfile(user_id=current_user.id)
    if current_user.profile is None: db.add(profile)
    for field in ("age_group", "interests", "goals", "preferences"):
        value = getattr(profile_in, field)
        if value is not None: setattr(profile, field, value)
    db.commit(); db.refresh(current_user)
    return current_user


@router.post("/palm/analyze", response_model=PalmReadingResponse)
def analyze_palm(payload: PalmReadingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        cv = palm_cv_service.analyze_palm_image(payload.image_base64)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    palm = PalmReading(user_id=current_user.id, **cv)
    db.add(palm); db.commit(); db.refresh(palm)
    context = ai_interpretation_service.gather_context(db, current_user)
    result = ai_interpretation_service.generate_palm_interpretation(current_user.full_name, context.get("goals", []), cv, age_group=context.get("age_group"), life_trend=context.get("life_trend"), personality=context.get("personality"))
    db.add(AIInterpretation(reading_type="palm", reading_id=palm.id, summary=result["summary"], detailed_insight=result["detailed_insight"], safety_disclaimer=result["safety_disclaimer"]))
    personality_alignment = GuidanceScoringService.calculate_personality_alignment(context.get("personality"))
    user_context = GuidanceScoringService.calculate_user_context(current_user.profile)
    consistency = GuidanceScoringService.calculate_consistency(db, current_user.id, "palm", palm.id)
    GuidanceScoringService.calculate_score(db, "palm", palm.id, user_id=current_user.id, personality_alignment=personality_alignment, user_context=user_context, reading_consistency=consistency)
    RecommendationEngine.generate_recommendations(db, current_user.id, context.get("goals", []), json.dumps(cv))
    db.add(Notification(user_id=current_user.id, title="Palm analysis completed", message="Your palm image was processed and the reading is available."))
    db.commit()
    return _palm_response(db, palm)


@router.get("/palm/readings", response_model=List[PalmReadingResponse])
def get_my_palm_readings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(PalmReading).filter(PalmReading.user_id == current_user.id).order_by(PalmReading.created_at.desc()).all()
    return [_palm_response(db, row) for row in rows]


@router.get("/tarot/cards", response_model=List[TarotCardResponse])
def get_tarot_deck(db: Session = Depends(get_db)):
    TarotDeckService.seed_tarot_deck(db)
    return db.query(TarotCard).order_by(TarotCard.id).all()


@router.post("/tarot/readings", response_model=TarotReadingResponse)
def perform_tarot_reading(payload: TarotReadingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    TarotDeckService.seed_tarot_deck(db)
    try:
        drawn = TarotDeckService.draw_spread(db, payload.spread_name, card_ids=payload.card_ids, reversed_flags=payload.reversed_flags)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    reading = TarotReading(user_id=current_user.id, spread_name=payload.spread_name, focus_intent=payload.focus_intent)
    db.add(reading); db.commit(); db.refresh(reading)
    for item in drawn:
        db.add(TarotReadingCard(reading_id=reading.id, card_id=item["card"].id, position_name=item["position_name"], is_reversed=item["is_reversed"]))
    db.commit(); db.refresh(reading)
    context = ai_interpretation_service.gather_context(db, current_user)
    result = ai_interpretation_service.generate_tarot_interpretation(current_user.full_name, payload.focus_intent or "General", drawn, age_group=context.get("age_group"), life_trend=context.get("life_trend"), personality=context.get("personality"))
    db.add(AIInterpretation(reading_type="tarot", reading_id=reading.id, summary=result["summary"], detailed_insight=result["detailed_insight"], safety_disclaimer=result["safety_disclaimer"]))
    GuidanceScoringService.calculate_score(db, "tarot", reading.id, user_id=current_user.id, personality_alignment=GuidanceScoringService.calculate_personality_alignment(context.get("personality")), user_context=GuidanceScoringService.calculate_user_context(current_user.profile), reading_consistency=GuidanceScoringService.calculate_consistency(db, current_user.id, "tarot", reading.id))
    RecommendationEngine.generate_recommendations(db, current_user.id, context.get("goals", []), json.dumps({"cards": [item["card"].name for item in drawn]}))
    db.add(Notification(user_id=current_user.id, title="Tarot reading completed", message="Your selected spread was recorded and interpreted.")); db.commit(); db.refresh(reading)
    return _tarot_response(db, reading)


@router.get("/tarot/readings", response_model=List[TarotReadingResponse])
def get_my_tarot_readings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(TarotReading).options(joinedload(TarotReading.cards_drawn).joinedload(TarotReadingCard.card)).filter(TarotReading.user_id == current_user.id).order_by(TarotReading.created_at.desc()).all()
    return [_tarot_response(db, row) for row in rows]


@router.post("/combined/analyze", response_model=CombinedMasterReportResponse)
def analyze_combined_master(payload: CombinedReadingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.palm_reading_id:
        palm = db.query(PalmReading).filter(PalmReading.id == payload.palm_reading_id, PalmReading.user_id == current_user.id).first()
        if not palm: raise HTTPException(status_code=404, detail="Palm reading not found.")
        palm_data = {k: getattr(palm, k) for k in ("palm_shape", "finger_structure", "life_line_conf", "head_line_conf", "heart_line_conf", "fate_line_conf", "sun_line_conf", "overall_conf", "image_path", "processed_image_path")}
    elif payload.image_base64:
        try: palm_data = palm_cv_service.analyze_palm_image(payload.image_base64)
        except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
        palm = PalmReading(user_id=current_user.id, **palm_data); db.add(palm); db.commit(); db.refresh(palm)
    else:
        raise HTTPException(status_code=400, detail="Provide an image or an existing palm reading owned by the current user.")

    TarotDeckService.seed_tarot_deck(db)
    try: drawn = TarotDeckService.draw_spread(db, payload.spread_name, card_ids=payload.card_ids, reversed_flags=payload.reversed_flags)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    tarot = TarotReading(user_id=current_user.id, spread_name=payload.spread_name, focus_intent=payload.focus_intent); db.add(tarot); db.commit(); db.refresh(tarot)
    formatted = []
    for item in drawn:
        card = item["card"]; db.add(TarotReadingCard(reading_id=tarot.id, card_id=card.id, position_name=item["position_name"], is_reversed=item["is_reversed"]))
        formatted.append({"card_name": card.name, "arcana": card.arcana, "position": item["position_name"], "orientation": "reversed" if item["is_reversed"] else "upright", "meaning": card.meaning_reversed if item["is_reversed"] else card.meaning_upright})
    db.commit()
    context = ai_interpretation_service.gather_context(db, current_user)
    report = ai_interpretation_service.generate_combined_master_report(current_user.full_name, context.get("goals", []), palm_data, formatted, payload.spread_name, payload.focus_intent or "General", age_group=context.get("age_group"), life_trend=context.get("life_trend"), personality=context.get("personality"), zodiac=context.get("zodiac"))
    db.add(AIInterpretation(reading_type="combined", reading_id=palm.id, summary=report["summary"], detailed_insight=json.dumps(report["categories"]), safety_disclaimer=report["safety_disclaimer"]))
    line_avg = sum(float(palm_data.get(k, 0)) for k in ("life_line_conf", "head_line_conf", "heart_line_conf", "fate_line_conf", "sun_line_conf")) / 5
    tarot_relevance = GuidanceScoringService.calculate_tarot_relevance(tarot)
    final_score = round(line_avg * .30 + tarot_relevance * .25 + GuidanceScoringService.calculate_personality_alignment(context.get("personality")) * .20 + GuidanceScoringService.calculate_user_context(current_user.profile) * .15 + GuidanceScoringService.calculate_consistency(db, current_user.id, "palm", palm.id) * .10, 1)
    recs = RecommendationEngine.generate_combined_recommendations(db, current_user.id, palm_data, formatted, payload.focus_intent or "General")
    db.add(GuidanceScore(reading_type="combined", reading_id=palm.id, palm_conf=line_avg, tarot_relevance=tarot_relevance, personality_alignment=GuidanceScoringService.calculate_personality_alignment(context.get("personality")), user_context=GuidanceScoringService.calculate_user_context(current_user.profile), reading_consistency=GuidanceScoringService.calculate_consistency(db, current_user.id, "palm", palm.id), final_score=final_score))
    db.add(Notification(user_id=current_user.id, title="Combined report generated", message="Your palm and tarot signals were synthesized into one master report.")); db.commit()
    return {"id": palm.id, "user_name": current_user.full_name, "summary": report["summary"], "composite_score": report["composite_score"], "categories": report["categories"], "palm_metrics": palm_data, "tarot_cards": formatted, "recommendations": [RecommendationResponse.model_validate(r).model_dump() for r in recs], "safety_disclaimer": report["safety_disclaimer"], "created_at": datetime.utcnow()}


@router.get("/insights/comprehensive", response_model=ComprehensiveInsightResponse)
def get_comprehensive_insight(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    context = ai_interpretation_service.gather_context(db, current_user)
    try: insight = ai_interpretation_service.generate_comprehensive_insight(context)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    return insight


@router.get("/insights/personality")
def get_personality_insight(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = ai_interpretation_service._build_reading_history(db, current_user.id)
    if not history: raise HTTPException(status_code=404, detail="Complete a reading before requesting a personality profile.")
    return PersonalityService.analyze_profile(history)


@router.get("/insights/life-trend")
def get_life_trend(current_user: User = Depends(get_current_user)):
    profile = current_user.profile
    if not profile or not profile.goals: raise HTTPException(status_code=404, detail="Add at least one goal before requesting life-trend analysis.")
    return LifeTrendService.calculate_trends(profile.age_group, profile.goals)


@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_my_recommendations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Recommendation).filter(Recommendation.user_id == current_user.id).order_by(Recommendation.created_at.desc()).all()


@router.put("/recommendations/{id}/complete", response_model=RecommendationResponse)
def complete_recommendation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.query(Recommendation).filter(Recommendation.id == id, Recommendation.user_id == current_user.id).first()
    if not rec: raise HTTPException(status_code=404, detail="Task not found")
    rec.is_completed = True; db.commit(); db.refresh(rec); return rec


@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()


@router.put("/notifications/{id}/read", response_model=NotificationResponse)
def read_notification(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == id, Notification.user_id == current_user.id).first()
    if not notif: raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True; db.commit(); db.refresh(notif); return notif


def _user_report_data(report_type: str, current_user: User, db: Session):
    """Build report payloads from persisted data owned by the authenticated user."""
    if report_type == "personality":
        history = ai_interpretation_service._build_reading_history(db, current_user.id)
        if not history:
            raise HTTPException(status_code=404, detail="Complete a reading before requesting a personality report.")
        profile = PersonalityService.analyze_profile(history)
        categories = {
            "personality_type": profile.get("personality_type"),
            "dominant_traits": ", ".join(profile.get("dominant_traits", [])),
            "strengths": "\n".join(profile.get("strengths", [])),
            "weaknesses": "\n".join(profile.get("weaknesses", [])),
            "behavioral_insights": profile.get("behavioral_insights"),
            "development_recommendations": "\n".join(profile.get("development_recommendations", [])),
            "big_five": ", ".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in (profile.get("big_five") or {}).items()),
        }
        return {
            "id": "PERSONALITY",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "type": "Personality Report",
            "focus": "Aggregated personality profile",
            "score": None,
            "summary": profile.get("summary"),
            "synthesis": profile.get("behavioral_insights"),
            "categories": categories,
            "disclaimer": "This report is intended for symbolic self-reflection and entertainment and is not professional advice.",
        }

    if report_type == "spiritual-guidance":
        palm_ids = [row.id for row in db.query(PalmReading.id).filter(PalmReading.user_id == current_user.id).all()]
        tarot_ids = [row.id for row in db.query(TarotReading.id).filter(TarotReading.user_id == current_user.id).all()]
        score_rows = db.query(GuidanceScore).filter(
            ((GuidanceScore.reading_type == "palm") & GuidanceScore.reading_id.in_(palm_ids))
            | ((GuidanceScore.reading_type == "tarot") & GuidanceScore.reading_id.in_(tarot_ids))
            | ((GuidanceScore.reading_type == "combined") & GuidanceScore.reading_id.in_(palm_ids))
        ).order_by(GuidanceScore.created_at.asc()).all()
        if not score_rows:
            raise HTTPException(status_code=404, detail="Complete a reading before requesting a spiritual guidance report.")
        recommendations = db.query(Recommendation).filter(Recommendation.user_id == current_user.id).all()
        average_score = round(sum(float(row.final_score) for row in score_rows) / len(score_rows), 2)
        latest = score_rows[-1]
        categories = {
            "average_guidance_score": str(average_score),
            "latest_guidance_score": str(round(float(latest.final_score), 2)),
            "latest_score_components": (
                f"Palm confidence: {round(float(latest.palm_conf), 2)}; "
                f"Tarot relevance: {round(float(latest.tarot_relevance), 2)}; "
                f"Personality alignment: {round(float(latest.personality_alignment), 2)}; "
                f"User context relevance: {round(float(latest.user_context), 2)}; "
                f"Reading consistency: {round(float(latest.reading_consistency), 2)}"
            ),
            "reading_scores": "\n".join(
                f"{row.created_at.strftime('%Y-%m-%d')}: {row.reading_type} — {round(float(row.final_score), 2)}"
                for row in score_rows
            ),
            "recommendations_total": str(len(recommendations)),
            "recommendations_completed": str(sum(1 for row in recommendations if row.is_completed)),
            "recommendation_completion_rate": str(round(sum(1 for row in recommendations if row.is_completed) / len(recommendations) * 100, 2) if recommendations else 0.0),
        }
        return {
            "id": "SPIRITUAL-GUIDANCE",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "type": "Spiritual Guidance Report",
            "focus": "Guidance scoring and recommendation effectiveness",
            "score": average_score,
            "summary": f"Guidance analysis based on {len(score_rows)} persisted reading score(s).",
            "synthesis": "The report summarizes the guidance scores and recommendation activity calculated from your persisted readings.",
            "categories": categories,
            "disclaimer": "This report is intended for symbolic self-reflection and entertainment and is not professional advice.",
        }

    if report_type == "insight-trend":
        profile = current_user.profile
        if not profile or not profile.goals:
            raise HTTPException(status_code=404, detail="Add at least one goal before requesting an insight trend report.")
        history = ai_interpretation_service._build_reading_history(db, current_user.id)
        if not history:
            raise HTTPException(status_code=404, detail="Complete a reading before requesting an insight trend report.")
        trends = LifeTrendService.calculate_trends(profile.age_group, profile.goals)
        palm_ids = [row.id for row in db.query(PalmReading.id).filter(PalmReading.user_id == current_user.id).all()]
        tarot_ids = [row.id for row in db.query(TarotReading.id).filter(TarotReading.user_id == current_user.id).all()]
        scores = db.query(GuidanceScore).filter(
            ((GuidanceScore.reading_type == "palm") & GuidanceScore.reading_id.in_(palm_ids))
            | ((GuidanceScore.reading_type == "tarot") & GuidanceScore.reading_id.in_(tarot_ids))
            | ((GuidanceScore.reading_type == "combined") & GuidanceScore.reading_id.in_(palm_ids))
        ).order_by(GuidanceScore.created_at.asc()).all()
        categories = {
            "life_path_stage": trends.get("life_path_stage"),
            "current_trends": "\n".join(trends.get("current_trends", [])),
            "upcoming_opportunities": "\n".join(trends.get("upcoming_opportunities", [])),
            "forecasted_challenges": "\n".join(trends.get("forecasted_challenges", [])),
            "growth_potential_rating": trends.get("growth_potential_rating"),
            "active_goals": "\n".join(str(goal) for goal in trends.get("active_goals", [])),
            "guidance_score_trend": "\n".join(
                f"{row.created_at.strftime('%Y-%m-%d')}: {row.reading_type} — {round(float(row.final_score), 2)}"
                for row in scores
            ) or "No persisted guidance scores available.",
        }
        return {
            "id": "INSIGHT-TREND",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "type": "Insight Trend Report",
            "focus": trends.get("life_path_stage", "Life trend analysis"),
            "score": round(sum(float(row.final_score) for row in scores) / len(scores), 2) if scores else None,
            "summary": f"Life-trend analysis based on your persisted goals and {len(history)} reading record(s).",
            "synthesis": "The trend analysis highlights the current life-path stage, goal-aligned opportunities, challenges, and persisted guidance-score history.",
            "categories": categories,
            "disclaimer": "This report is intended for symbolic self-reflection and entertainment and is not professional advice.",
        }

    raise HTTPException(status_code=400, detail="Unsupported report type")


@router.get("/reports/pdf/personality")
def export_personality_pdf(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pdf = ReportGenerator.generate_pdf_report(_user_report_data("personality", current_user, db))
    return Response(pdf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="aetheria_personality_report.pdf"'})


@router.get("/reports/excel/personality")
def export_personality_excel(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    excel = ReportGenerator.generate_excel_report(_user_report_data("personality", current_user, db))
    return Response(excel.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="aetheria_personality_report.xlsx"'})


@router.get("/reports/pdf/spiritual-guidance")
def export_spiritual_guidance_pdf(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pdf = ReportGenerator.generate_pdf_report(_user_report_data("spiritual-guidance", current_user, db))
    return Response(pdf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="aetheria_spiritual_guidance_report.pdf"'})


@router.get("/reports/excel/spiritual-guidance")
def export_spiritual_guidance_excel(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    excel = ReportGenerator.generate_excel_report(_user_report_data("spiritual-guidance", current_user, db))
    return Response(excel.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="aetheria_spiritual_guidance_report.xlsx"'})


@router.get("/reports/pdf/insight-trend")
def export_insight_trend_pdf(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pdf = ReportGenerator.generate_pdf_report(_user_report_data("insight-trend", current_user, db))
    return Response(pdf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="aetheria_insight_trend_report.pdf"'})


@router.get("/reports/excel/insight-trend")
def export_insight_trend_excel(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    excel = ReportGenerator.generate_excel_report(_user_report_data("insight-trend", current_user, db))
    return Response(excel.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="aetheria_insight_trend_report.xlsx"'})


@router.get("/reports/pdf/{reading_type}/{reading_id}")
def export_pdf(reading_type: str, reading_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if reading_type not in {"palm", "tarot", "combined"}: raise HTTPException(status_code=400, detail="Unsupported reading type")
    if reading_type == "palm" or reading_type == "combined":
        reading = db.query(PalmReading).filter(PalmReading.id == reading_id, PalmReading.user_id == current_user.id).first()
        if not reading: raise HTTPException(status_code=404, detail="Record not found")
        focus = reading.palm_shape or "Palm analysis"
    else:
        reading = db.query(TarotReading).filter(TarotReading.id == reading_id, TarotReading.user_id == current_user.id).first()
        if not reading: raise HTTPException(status_code=404, detail="Record not found")
        focus = reading.spread_name
    ai = _ai(db, reading_type, reading_id) or (_ai(db, "combined", reading_id) if reading_type == "combined" else None)
    score = _score(db, reading_type, reading_id) or (_score(db, "combined", reading_id) if reading_type == "combined" else None)
    if not ai: raise HTTPException(status_code=404, detail="No generated interpretation exists for this report.")
    data = {"id": f"{reading_type.upper()}-{reading_id}", "date": reading.created_at.strftime("%Y-%m-%d"), "type": f"{reading_type.capitalize()} Analysis", "focus": focus, "score": score.final_score if score else None, "synthesis": ai.detailed_insight, "summary": ai.summary, "disclaimer": ai.safety_disclaimer}
    if reading_type == "tarot":
        tarot = db.query(TarotReading).options(joinedload(TarotReading.cards_drawn).joinedload(TarotReadingCard.card)).filter(TarotReading.id == reading_id, TarotReading.user_id == current_user.id).first()
        data["tarot_cards"] = [{"position": c.position_name, "card_name": c.card.name, "orientation": "reversed" if c.is_reversed else "upright", "meaning": c.card.meaning_reversed if c.is_reversed else c.card.meaning_upright} for c in (tarot.cards_drawn if tarot else [])]
    if reading_type == "combined":
        try: data["categories"] = json.loads(ai.detailed_insight)
        except (TypeError, ValueError): pass
    pdf = ReportGenerator.generate_pdf_report(data)
    return Response(pdf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="aetheria_{reading_type}_{reading_id}.pdf"'})


@router.get("/reports/excel/{reading_type}/{reading_id}")
def export_excel(reading_type: str, reading_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if reading_type not in {"palm", "tarot", "combined"}: raise HTTPException(status_code=400, detail="Unsupported reading type")
    owner_query = db.query(PalmReading if reading_type in {"palm", "combined"} else TarotReading)
    reading = owner_query.filter((PalmReading.id if reading_type in {"palm", "combined"} else TarotReading.id) == reading_id, (PalmReading.user_id if reading_type in {"palm", "combined"} else TarotReading.user_id) == current_user.id).first()
    if not reading: raise HTTPException(status_code=404, detail="Record not found")
    ai = _ai(db, reading_type, reading_id) or (_ai(db, "combined", reading_id) if reading_type == "combined" else None)
    score = _score(db, reading_type, reading_id) or (_score(db, "combined", reading_id) if reading_type == "combined" else None)
    if not ai: raise HTTPException(status_code=404, detail="No generated interpretation exists for this report.")
    data = {"id": f"{reading_type.upper()}-{reading_id}", "date": reading.created_at.strftime("%Y-%m-%d"), "type": f"{reading_type.capitalize()} Analysis", "focus": getattr(reading, "spread_name", None) or getattr(reading, "palm_shape", None) or "Combined", "score": score.final_score if score else None, "summary": ai.summary, "synthesis": ai.detailed_insight, "disclaimer": ai.safety_disclaimer}
    if reading_type == "tarot":
        tarot = db.query(TarotReading).options(joinedload(TarotReading.cards_drawn).joinedload(TarotReadingCard.card)).filter(TarotReading.id == reading_id, TarotReading.user_id == current_user.id).first()
        data["tarot_cards"] = [{"position": c.position_name, "card_name": c.card.name, "orientation": "reversed" if c.is_reversed else "upright", "meaning": c.card.meaning_reversed if c.is_reversed else c.card.meaning_upright} for c in (tarot.cards_drawn if tarot else [])]
    if reading_type == "combined":
        try: data["categories"] = json.loads(ai.detailed_insight)
        except (TypeError, ValueError): pass
    excel = ReportGenerator.generate_excel_report(data)
    return Response(excel.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="aetheria_{reading_type}_{reading_id}.xlsx"'})


@router.get("/reports/excel/consultant")
def export_consultant_analytics(current_user: User = Depends(RoleChecker(["SPIRITUAL_CONSULTANT", "ADMINISTRATOR"])), db: Session = Depends(get_db)):
    from backend.app.api.analytics import consultant_dashboard
    analytics = consultant_dashboard(db)
    metrics = {
        "client_count": analytics.client_count,
        "reading_count": analytics.reading_count,
        "average_guidance_score": analytics.average_guidance_score,
    }
    excel = ReportGenerator.generate_analytics_excel_report("AETHERIA — Consultant Analytics", metrics, analytics.readings_by_day)
    return Response(excel.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="aetheria_consultant_analytics.xlsx"'})


@router.get("/reader/queue", dependencies=[Depends(RoleChecker(["TAROT_READER", "ADMINISTRATOR"]))])
def get_reader_queue(db: Session = Depends(get_db)):
    readings = db.query(TarotReading).order_by(TarotReading.created_at.desc()).limit(50).all()
    return {"queue_length": len(readings), "readings": readings}


@router.get("/consultant/clients", dependencies=[Depends(RoleChecker(["SPIRITUAL_CONSULTANT", "ADMINISTRATOR"]))])
def get_consultant_clients(db: Session = Depends(get_db)):
    clients = db.query(User).filter(User.role == "USER").order_by(User.created_at.desc()).all()
    return {"total_clients": len(clients), "clients": clients}
