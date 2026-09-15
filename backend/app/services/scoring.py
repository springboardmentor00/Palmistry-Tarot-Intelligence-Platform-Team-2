from sqlalchemy.orm import Session
from backend.app.models.sql_models import GuidanceScore, PalmReading, TarotReading


class GuidanceScoringService:
    @staticmethod
    def calculate_palm_confidence(palm_reading: PalmReading) -> float:
        values = [palm_reading.life_line_conf, palm_reading.head_line_conf, palm_reading.heart_line_conf, palm_reading.fate_line_conf, palm_reading.sun_line_conf]
        valid = [float(v) for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else 0.0

    @staticmethod
    def calculate_tarot_relevance(tarot_reading: TarotReading) -> float:
        cards = tarot_reading.cards_drawn or []
        if not cards:
            return 0.0
        major = sum(1 for c in cards if getattr(getattr(c, "card", None), "arcana", "").lower() == "major")
        return round(75.0 + (major / len(cards)) * 20.0, 2)

    @staticmethod
    def calculate_personality_alignment(personality: dict | None) -> float:
        if not personality:
            return 0.0
        traits = len(personality.get("dominant_traits", []))
        strengths = len(personality.get("strengths", []))
        return round(min(100.0, 55.0 + traits * 8.0 + strengths * 4.0), 2)

    @staticmethod
    def calculate_user_context(profile) -> float:
        if not profile:
            return 0.0
        goals = profile.goals or []
        interests = profile.interests or []
        return round(min(100.0, 50.0 + len(goals) * 10.0 + len(interests) * 5.0), 2)

    @staticmethod
    def calculate_consistency(db: Session, user_id: int, current_type: str, current_id: int) -> float:
        # Consistency measures how many prior readings of the same type exist; it
        # is intentionally neutral for a first reading rather than fabricated.
        prior = 0
        if current_type == "palm":
            prior = db.query(PalmReading).filter(PalmReading.user_id == user_id, PalmReading.id != current_id).count()
        elif current_type == "tarot":
            prior = db.query(TarotReading).filter(TarotReading.user_id == user_id, TarotReading.id != current_id).count()
        return round(min(100.0, 50.0 + prior * 10.0), 2) if prior else 50.0

    @staticmethod
    def calculate_score(db: Session, reading_type: str, reading_id: int, *, user_id: int, palm_conf: float | None = None, tarot_relevance: float | None = None, personality_alignment: float | None = None, user_context: float | None = None, reading_consistency: float | None = None) -> GuidanceScore:
        palm = db.query(PalmReading).filter(PalmReading.id == reading_id, PalmReading.user_id == user_id).first() if reading_type == "palm" else None
        tarot = db.query(TarotReading).filter(TarotReading.id == reading_id, TarotReading.user_id == user_id).first() if reading_type == "tarot" else None
        if reading_type == "palm" and palm is None:
            raise ValueError("Palm reading not found for this user.")
        if reading_type == "tarot" and tarot is None:
            raise ValueError("Tarot reading not found for this user.")
        if palm_conf is None:
            palm_conf = GuidanceScoringService.calculate_palm_confidence(palm) if palm else 0.0
        if tarot_relevance is None:
            tarot_relevance = GuidanceScoringService.calculate_tarot_relevance(tarot) if tarot else 0.0
        # Callers may supply contextual dimensions; absent values remain neutral
        # rather than pretending a measurement was observed.
        personality_alignment = 0.0 if personality_alignment is None else personality_alignment
        user_context = 0.0 if user_context is None else user_context
        reading_consistency = 0.0 if reading_consistency is None else reading_consistency
        final_score = round(max(0.0, min(100.0, palm_conf * .30 + tarot_relevance * .25 + personality_alignment * .20 + user_context * .15 + reading_consistency * .10)), 1)
        row = GuidanceScore(reading_type=reading_type, reading_id=reading_id, palm_conf=palm_conf, tarot_relevance=tarot_relevance, personality_alignment=personality_alignment, user_context=user_context, reading_consistency=reading_consistency, final_score=final_score)
        db.add(row)
        db.commit(); db.refresh(row)
        return row
