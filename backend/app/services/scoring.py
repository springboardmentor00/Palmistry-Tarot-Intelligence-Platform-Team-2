from sqlalchemy.orm import Session
from backend.app.models.sql_models import GuidanceScore, PalmReading, TarotReading


class GuidanceScoringService:
    @staticmethod
    def calculate_palm_confidence(palm_reading: PalmReading) -> float:
        """Dynamically calculates overall palm confidence from all detected line confidences."""
        lines = [
            getattr(palm_reading, "life_line_conf", None),
            getattr(palm_reading, "head_line_conf", None),
            getattr(palm_reading, "heart_line_conf", None),
            getattr(palm_reading, "fate_line_conf", None),
            getattr(palm_reading, "sun_line_conf", None),
        ]
        valid_lines = [c for c in lines if c is not None and c > 0]
        if not valid_lines:
            return float(getattr(palm_reading, "overall_conf", 70.0) or 70.0)
        return round(sum(valid_lines) / len(valid_lines), 2)

    @staticmethod
    def calculate_tarot_relevance(tarot_reading: TarotReading) -> float:
        """Calculates relevance score based on card draw completeness and Major Arcana weighting."""
        cards = getattr(tarot_reading, "cards_drawn", []) or []
        if not cards:
            return 70.0

        major_count = 0
        total_cards = len(cards)

        for c in cards:
            card_obj = getattr(c, "card", None)
            arcana = getattr(card_obj, "arcana", "") if card_obj else ""
            if arcana and str(arcana).lower() == "major":
                major_count += 1

        # Major Arcana cards carry higher spiritual/guidance weight
        base_relevance = 75.0
        bonus = (major_count / total_cards) * 20.0
        return round(min(100.0, base_relevance + bonus), 2)

    @staticmethod
    def calculate_score(
        db: Session,
        reading_type: str,
        reading_id: int,
        palm_conf: float = 80.0,
        tarot_relevance: float = 80.0,
        personality_alignment: float = 80.0,
        user_context: float = 80.0,
        reading_consistency: float = 80.0,
    ) -> GuidanceScore:
        """Calculates and persists a weighted guidance score for a reading."""

        # Fetch underlying reading models if default metrics need dynamic computation
        if reading_type == "palm":
            palm_reading = db.query(PalmReading).filter(PalmReading.id == reading_id).first()
            if palm_reading:
                palm_conf = GuidanceScoringService.calculate_palm_confidence(palm_reading)
        elif reading_type == "tarot":
            tarot_reading = db.query(TarotReading).filter(TarotReading.id == reading_id).first()
            if tarot_reading:
                tarot_relevance = GuidanceScoringService.calculate_tarot_relevance(tarot_reading)

        # Guidance Score Formula:
        # (Palm * 0.30) + (Tarot * 0.25) + (Personality * 0.20) + (User * 0.15) + (Consistency * 0.10)
        weighted_score = (
            (palm_conf * 0.30)
            + (tarot_relevance * 0.25)
            + (personality_alignment * 0.20)
            + (user_context * 0.15)
            + (reading_consistency * 0.10)
        )

        # Ensure normalization between 0.0 and 100.0
        final_score = max(0.0, min(100.0, weighted_score))
        final_score = round(final_score, 1)

        db_score = GuidanceScore(
            reading_type=reading_type,
            reading_id=reading_id,
            palm_conf=palm_conf,
            tarot_relevance=tarot_relevance,
            personality_alignment=personality_alignment,
            user_context=user_context,
            reading_consistency=reading_consistency,
            final_score=final_score,
        )

        db.add(db_score)
        db.commit()
        db.refresh(db_score)

        return db_score
