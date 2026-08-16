from sqlalchemy.orm import Session
from backend.app.models.sql_models import Recommendation

class RecommendationEngine:
    @staticmethod
    def generate_recommendations(db: Session, user_id: int, goals: list, reading_context: str) -> list:
        # Predefined recommendations mapped to user goals
        recommendation_catalog = {
            "Self Reflection": [
                ("Journaling Reflection", "Write a 500-word daily review based on your latest archetype symbols.", "growth"),
                ("Silence Practice", "Spend 10 minutes in silence reflecting upon the theme of decision boundaries.", "growth")
            ],
            "Relationship Alignment": [
                ("Active Listening", "Exercise high empathy listening during your next family/partner conversation.", "relationship"),
                ("Emotional Boundary setting", "Communicate one key boundary plan clearly to your partner or colleague.", "relationship")
            ],
            "Career Paths": [
                ("Skill Mapping", "Outline how your analytical Head Line traits align to your active project role.", "career"),
                ("Objective Target Review", "Set three actionable milestones that match your long-term values.", "career")
            ],
            "Decision Guidance": [
                ("Decision Table", "Create a binary logic list for your current choice, weighting values.", "career"),
                ("Oracle Walk", "Take a 15-minute nature walk contemplating options without screen distractions.", "growth")
            ]
        }

        generated = []
        
        # Pick recommendations matching user goals
        for goal in goals:
            if goal in recommendation_catalog:
                for title, desc, cat in recommendation_catalog[goal]:
                    # Create recommendation record
                    rec = Recommendation(
                        user_id=user_id,
                        category=cat,
                        title=title,
                        description=desc,
                        is_completed=False
                    )
                    db.add(rec)
                    generated.append(rec)
        
        # Fallback if no goals matched
        if not generated:
            rec = Recommendation(
                user_id=user_id,
                category="growth",
                title="Mindful Breathing",
                description="Adopt a 4-7-8 breathing sequence during daily workspace transitions.",
                is_completed=False
            )
            db.add(rec)
            generated.append(rec)

        db.commit()
        return generated
 
