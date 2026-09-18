from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.auth import require_roles, get_current_user
from backend.app.database.postgres import get_db
from backend.app.models.sql_models import AIInterpretation, GuidanceScore, PalmReading, Recommendation, TarotReading, User
from backend.app.schemas.pydantic_schemas import ExecutiveAnalyticsResponse, SpecialistAnalyticsResponse, UserAnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _days_30():
    today = datetime.utcnow().date()
    return [today - timedelta(days=i) for i in range(29, -1, -1)]


@router.get("/user", response_model=UserAnalyticsResponse)
def user_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    palm = db.query(PalmReading).filter(PalmReading.user_id == current_user.id).count()
    tarot = db.query(TarotReading).filter(TarotReading.user_id == current_user.id).count()
    scores = db.query(GuidanceScore).filter(GuidanceScore.reading_id.in_([r.id for r in db.query(PalmReading.id).filter(PalmReading.user_id == current_user.id).all()])) if False else db.query(GuidanceScore).filter(GuidanceScore.reading_type.in_(["palm", "tarot", "combined"])).all()
    # Scope score rows to IDs owned by this user.
    palm_ids = {r.id for r in db.query(PalmReading.id).filter(PalmReading.user_id == current_user.id).all()}
    tarot_ids = {r.id for r in db.query(TarotReading.id).filter(TarotReading.user_id == current_user.id).all()}
    scores = [s for s in scores if (s.reading_type == "palm" and s.reading_id in palm_ids) or (s.reading_type == "tarot" and s.reading_id in tarot_ids) or (s.reading_type == "combined" and s.reading_id in palm_ids)]
    avg = sum(s.final_score for s in scores) / len(scores) if scores else None
    recs = db.query(Recommendation).filter(Recommendation.user_id == current_user.id).all()
    by_day = {d.isoformat(): {"date": d.isoformat(), "count": 0} for d in _days_30()}
    score_day = {d.isoformat(): {"date": d.isoformat(), "average": None} for d in _days_30()}
    all_readings = db.query(PalmReading).filter(PalmReading.user_id == current_user.id).all() + db.query(TarotReading).filter(TarotReading.user_id == current_user.id).all()
    for r in all_readings:
        key = r.created_at.date().isoformat()
        if key in by_day: by_day[key]["count"] += 1
    for s in scores:
        # Use score creation date; it is tied to the user's scoped reading IDs.
        key = s.created_at.date().isoformat()
        if key in score_day:
            current = score_day[key].get("_values", [])
            current.append(float(s.final_score)); score_day[key]["_values"] = current
    score_series = []
    for item in score_day.values():
        vals = item.pop("_values", [])
        item["average"] = round(sum(vals) / len(vals), 2) if vals else None
        score_series.append(item)
    recent = sorted([{"type": "palm", "id": r.id, "created_at": r.created_at.isoformat(), "title": r.palm_shape or "Palm analysis"} for r in db.query(PalmReading).filter(PalmReading.user_id == current_user.id).all()] + [{"type": "tarot", "id": r.id, "created_at": r.created_at.isoformat(), "title": r.spread_name} for r in db.query(TarotReading).filter(TarotReading.user_id == current_user.id).all()], key=lambda x: x["created_at"], reverse=True)[:10]
    return UserAnalyticsResponse(reading_count=palm + tarot, palm_readings=palm, tarot_readings=tarot, average_guidance_score=round(avg, 2) if avg is not None else None, recommendation_count=len(recs), completed_recommendations=sum(1 for r in recs if r.is_completed), completion_rate=round(sum(1 for r in recs if r.is_completed) / len(recs) * 100, 2) if recs else 0.0, readings_by_day=list(by_day.values()), score_by_day=score_series, recent_readings=recent)


@router.get("/executive", response_model=ExecutiveAnalyticsResponse, dependencies=[Depends(require_roles(["ADMINISTRATOR"]))])
def executive_dashboard(db: Session = Depends(get_db)):
    from backend.app.main import telemetry
    users = db.query(User).count(); active = db.query(User).filter(User.is_active.is_(True)).count()
    cutoff = datetime.utcnow() - timedelta(days=30)
    new_users = db.query(User).filter(User.created_at >= cutoff).count()
    palms = db.query(PalmReading).count(); tarot = db.query(TarotReading).count()
    avg = db.query(func.avg(GuidanceScore.final_score)).scalar()
    rec_total = db.query(Recommendation).count(); rec_done = db.query(Recommendation).filter(Recommendation.is_completed.is_(True)).count()
    role_rows = db.query(User.role, func.count(User.id)).group_by(User.role).all(); roles = {role: count for role, count in role_rows}
    readings_by_day = {d.isoformat(): {"date": d.isoformat(), "count": 0} for d in _days_30()}
    scores_by_day = {d.isoformat(): {"date": d.isoformat(), "average": None, "_values": []} for d in _days_30()}
    for created in db.query(PalmReading.created_at).all() + db.query(TarotReading.created_at).all():
        key = created[0].date().isoformat()
        if key in readings_by_day: readings_by_day[key]["count"] += 1
    for score in db.query(GuidanceScore).filter(GuidanceScore.created_at >= cutoff).all():
        key = score.created_at.date().isoformat()
        if key in scores_by_day: scores_by_day[key]["_values"].append(float(score.final_score))
    score_series = []
    for item in scores_by_day.values():
        vals = item.pop("_values"); item["average"] = round(sum(vals) / len(vals), 2) if vals else None; score_series.append(item)
    return ExecutiveAnalyticsResponse(total_users=users, active_users=active, new_users_30d=new_users, total_readings=palms + tarot, palm_readings=palms, tarot_readings=tarot, average_guidance_score=round(float(avg), 2) if avg is not None else None, recommendation_completion_rate=round(rec_done / rec_total * 100, 2) if rec_total else 0.0, role_breakdown=roles, readings_by_day=list(readings_by_day.values()), scores_by_day=score_series, api_requests=telemetry["requests"], average_api_latency_ms=round(telemetry["latency_total_ms"] / telemetry["requests"], 2) if telemetry["requests"] else None, error_requests=telemetry["errors"])


@router.get("/reader", response_model=SpecialistAnalyticsResponse, dependencies=[Depends(require_roles(["TAROT_READER", "ADMINISTRATOR"]))])
def reader_dashboard(db: Session = Depends(get_db)):
    """Reader-facing analytics built only from persisted Tarot reading records."""
    from backend.app.models.sql_models import TarotReadingCard, TarotCard, AIInterpretation

    rows = db.query(TarotReading).order_by(TarotReading.created_at.desc()).limit(100).all()
    client_counts = (
        db.query(TarotReading.user_id, func.count(TarotReading.id))
        .group_by(TarotReading.user_id)
        .all()
    )
    client_count = len(client_counts)
    repeat_client_count = sum(1 for _, count in client_counts if count > 1)

    cutoff = datetime.utcnow() - timedelta(days=29)
    recent_rows = db.query(TarotReading).filter(TarotReading.created_at >= cutoff).all()
    active_days = {row.created_at.date().isoformat() for row in recent_rows}

    by_day = {d.isoformat(): {"date": d.isoformat(), "count": 0} for d in _days_30()}
    for row in recent_rows:
        key = row.created_at.date().isoformat()
        if key in by_day:
            by_day[key]["count"] += 1

    ids = [r.id for r in rows]
    avg = (
        db.query(func.avg(GuidanceScore.final_score))
        .filter(GuidanceScore.reading_type == "tarot", GuidanceScore.reading_id.in_(ids))
        .scalar()
        if ids else None
    )

    breakdown_rows = (
        db.query(TarotCard.suit, func.count(TarotReadingCard.id))
        .join(TarotReadingCard, TarotReadingCard.card_id == TarotCard.id)
        .join(TarotReading, TarotReading.id == TarotReadingCard.reading_id)
        .group_by(TarotCard.suit)
        .all()
    )
    breakdown = {(suit or "Major Arcana"): int(count) for suit, count in breakdown_rows}

    interpretation_ids = {
        reading_id for (reading_id,) in db.query(AIInterpretation.reading_id)
        .filter(AIInterpretation.reading_type == "tarot", AIInterpretation.reading_id.in_(ids)).all()
    } if ids else set()
    score_ids = {
        reading_id for (reading_id,) in db.query(GuidanceScore.reading_id)
        .filter(GuidanceScore.reading_type == "tarot", GuidanceScore.reading_id.in_(ids)).all()
    } if ids else set()

    recent_readings = []
    for row in rows[:20]:
        recent_readings.append({
            "id": row.id,
            "user_id": row.user_id,
            "spread_name": row.spread_name,
            "focus_intent": row.focus_intent,
            "created_at": row.created_at.isoformat(),
            "has_interpretation": row.id in interpretation_ids,
            "has_guidance_score": row.id in score_ids,
            "report_ready": row.id in interpretation_ids,
        })

    reading_count = db.query(TarotReading).count()
    latest_session_at = rows[0].created_at.isoformat() if rows else None
    avg_per_client = round(reading_count / client_count, 2) if client_count else None
    repeat_rate = round(repeat_client_count / client_count * 100, 2) if client_count else 0.0

    return SpecialistAnalyticsResponse(
        client_count=client_count,
        reading_count=reading_count,
        average_guidance_score=round(float(avg), 2) if avg is not None else None,
        readings_by_day=list(by_day.values()),
        recent_readings=recent_readings,
        category_breakdown=breakdown,
        repeat_client_count=repeat_client_count,
        readings_30d=len(recent_rows),
        active_days_30d=len(active_days),
        average_readings_per_client=avg_per_client,
        repeat_client_rate=repeat_rate,
        latest_session_at=latest_session_at,
        report_ready_count=sum(1 for row in rows[:20] if row.id in interpretation_ids),
    )


@router.get("/consultant", response_model=SpecialistAnalyticsResponse, dependencies=[Depends(require_roles(["SPIRITUAL_CONSULTANT", "ADMINISTRATOR"]))])
def consultant_dashboard(db: Session = Depends(get_db)):
    rows = db.query(PalmReading).order_by(PalmReading.created_at.desc()).limit(100).all()
    client_count = db.query(func.count(func.distinct(PalmReading.user_id))).scalar() or 0
    reading_count = db.query(PalmReading).count()
    ids = [r.id for r in rows]

    score_rows = db.query(GuidanceScore).filter(
        GuidanceScore.reading_type == "palm",
        GuidanceScore.reading_id.in_(ids),
    ).all() if ids else []
    avg = sum(float(s.final_score) for s in score_rows) / len(score_rows) if score_rows else None

    cutoff = datetime.utcnow() - timedelta(days=29)
    by_day = {d.isoformat(): {"date": d.isoformat(), "count": 0, "average": None, "_values": []} for d in _days_30()}
    for created, in db.query(PalmReading.created_at).filter(PalmReading.created_at >= cutoff).all():
        key = created.date().isoformat()
        if key in by_day:
            by_day[key]["count"] += 1
    for created, value in db.query(GuidanceScore.created_at, GuidanceScore.final_score).filter(
        GuidanceScore.reading_type == "palm", GuidanceScore.created_at >= cutoff
    ).all():
        key = created.date().isoformat()
        if key in by_day:
            by_day[key]["_values"].append(float(value))
    for item in by_day.values():
        values = item.pop("_values")
        item["average"] = round(sum(values) / len(values), 2) if values else None

    client_counts = db.query(PalmReading.user_id, func.count(PalmReading.id)).group_by(PalmReading.user_id).all()
    repeat_client_count = sum(1 for _, count in client_counts if count > 1)
    repeat_rate = round(repeat_client_count / client_count * 100, 2) if client_count else 0.0
    active_days = {r.created_at.date().isoformat() for r in rows if r.created_at >= cutoff}

    interpretation_ids = {
        reading_id for reading_id, in db.query(AIInterpretation.reading_id).filter(
            AIInterpretation.reading_type == "palm", AIInterpretation.reading_id.in_(ids)
        ).all()
    } if ids else set()
    score_ids = {s.reading_id for s in score_rows}

    recent_readings = [{
        "id": r.id,
        "user_id": r.user_id,
        "palm_shape": r.palm_shape,
        "created_at": r.created_at.isoformat(),
        "has_guidance_score": r.id in score_ids,
        "report_ready": r.id in interpretation_ids,
    } for r in rows[:20]]

    return SpecialistAnalyticsResponse(
        client_count=client_count,
        reading_count=reading_count,
        average_guidance_score=round(float(avg), 2) if avg is not None else None,
        readings_by_day=list(by_day.values()),
        recent_readings=recent_readings,
        category_breakdown={},
        repeat_client_count=repeat_client_count,
        readings_30d=sum(item["count"] for item in by_day.values()),
        active_days_30d=len(active_days),
        average_readings_per_client=round(reading_count / client_count, 2) if client_count else None,
        repeat_client_rate=repeat_rate,
        latest_session_at=rows[0].created_at.isoformat() if rows else None,
        report_ready_count=sum(1 for r in rows[:20] if r.id in interpretation_ids),
    )
