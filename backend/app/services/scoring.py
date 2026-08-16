from sqlalchemy.orm import Session
from backend.app.models.sql_models import GuidanceScore

class GuidanceScoringService:
    @staticmethod
    def calculate_score(
        db: Session,
        reading_type: str,
        reading_id: int,
        palm_conf: float = 80.0,
        tarot_relevance: float = 80.0,
        personality_alignment: float = 80.0,
        user_context: float = 80.0,
        reading_consistency: float = 80.0
    ) -> GuidanceScore:
        
        # Formula:
        # Insight Score = (Palm * 0.30) + (Tarot * 0.25) + (Personality * 0.20) + (User * 0.15) + (Consistency * 0.10)
        weighted_score = (
            (palm_conf * 0.30) +
            (tarot_relevance * 0.25) +
            (personality_alignment * 0.20) +
            (user_context * 0.15) +
            (reading_consistency * 0.10)
        )
        
        # Ensure normalization between 0 and 100
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
            final_score=final_score
        )
        
        db.add(db_score)
        db.commit()
        db.refresh(db_score)
        
        return db_score
