import time
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db
from backend.app.models.sql_models import (
    User,
    PalmReading,
    TarotReading,
    TarotReadingCard,
    TarotCard,
    GuidanceScore,
)
from backend.app.schemas.pydantic_schemas import AdminAnalyticsResponse
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.sql_models import User as UserModel

router = APIRouter(prefix="/analytics", tags=["Analytics"])

require_analytics_access = RoleChecker(["ADMINISTRATOR", "SPIRITUAL_CONSULTANT"])


@router.get("/overview", response_model=AdminAnalyticsResponse)
def get_overview(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_analytics_access),
):
    """High-level platform metrics for the admin dashboard."""
    start_time = time.perf_counter()

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712

    palm_count = db.query(PalmReading).count()
    tarot_count = db.query(TarotReading).count()
    total_readings = palm_count + tarot_count

    avg_score = db.query(func.avg(GuidanceScore.final_score)).scalar() or 0.0

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    return AdminAnalyticsResponse(
        total_users=total_users,
        active_users=active_users,
        total_readings=total_readings,
        palm_readings=palm_count,
        tarot_readings=tarot_count,
        avg_guidance_score=round(float(avg_score), 2),
        api_response_time_ms=elapsed_ms,
    )


@router.get("/readings-trend")
def readings_trend(
    days: int = Query(30, ge=1, le=365, description="Number of past days to include"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_analytics_access),
):
    """Daily count of palm + tarot readings over the last N days, for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    palm_rows = (
        db.query(func.date(PalmReading.created_at).label("day"), func.count(PalmReading.id))
        .filter(PalmReading.created_at >= since)
        .group_by("day")
        .all()
    )
    tarot_rows = (
        db.query(func.date(TarotReading.created_at).label("day"), func.count(TarotReading.id))
        .filter(TarotReading.created_at >= since)
        .group_by("day")
        .all()
    )

    trend = {}
    for day, count in palm_rows:
        day_str = str(day)
        trend.setdefault(day_str, {"date": day_str, "palm_readings": 0, "tarot_readings": 0})
        trend[day_str]["palm_readings"] = count
    for day, count in tarot_rows:
        day_str = str(day)
        trend.setdefault(day_str, {"date": day_str, "palm_readings": 0, "tarot_readings": 0})
        trend[day_str]["tarot_readings"] = count

    return sorted(trend.values(), key=lambda x: x["date"])


@router.get("/top-tarot-cards")
def top_tarot_cards(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_analytics_access),
):
    """Most frequently drawn tarot cards across all readings."""
    rows = (
        db.query(TarotCard.name, TarotCard.arcana, func.count(TarotReadingCard.id).label("draw_count"))
        .join(TarotReadingCard, TarotReadingCard.card_id == TarotCard.id)
        .group_by(TarotCard.id)
        .order_by(func.count(TarotReadingCard.id).desc())
        .limit(limit)
        .all()
    )
    return [{"name": name, "arcana": arcana, "draw_count": draw_count} for name, arcana, draw_count in rows]


@router.get("/guidance-score-breakdown")
def guidance_score_breakdown(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_analytics_access),
):
    """Average value of each guidance score component, platform-wide."""
    result = db.query(
        func.avg(GuidanceScore.palm_conf),
        func.avg(GuidanceScore.tarot_relevance),
        func.avg(GuidanceScore.personality_alignment),
        func.avg(GuidanceScore.user_context),
        func.avg(GuidanceScore.reading_consistency),
        func.avg(GuidanceScore.final_score),
    ).first()

    keys = [
        "avg_palm_conf",
        "avg_tarot_relevance",
        "avg_personality_alignment",
        "avg_user_context",
        "avg_reading_consistency",
        "avg_final_score",
    ]
    return {k: round(float(v), 3) if v is not None else 0.0 for k, v in zip(keys, result)}


@router.get("/user-growth")
def user_growth(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_analytics_access),
):
    """New user signups per day over the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date(User.created_at).label("day"), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "new_users": count} for day, count in rows]