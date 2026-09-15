from typing import List
from sqlalchemy.orm import Session
from backend.app.models.sql_models import Recommendation


class RecommendationEngine:
    @staticmethod
    def generate_recommendations(db: Session, user_id: int, goals: list, reading_context: str) -> list:
        """Create practical recommendations from the user's actual goals/context.

        This engine never fabricates readings or users. The text is deterministic so
        the platform remains usable when an external LLM is not configured.
        """
        goal_text = ", ".join(str(g) for g in (goals or [])) or "personal reflection"
        context = str(reading_context or "").strip()
        templates = [
            ("career", "Convert insight into one measurable goal", f"Choose one action connected to {goal_text} and define a measurable outcome for the next review period. Use the completed reading only as a reflection prompt."),
            ("relationship", "Practice intentional communication", "Use one theme from your completed reading to start a clear, respectful conversation while keeping decisions grounded in the actual circumstances."),
            ("growth", "Keep a short reflection log", "Record one observation from the completed reading and one concrete action each day. Review the pattern after seven entries rather than treating a single reading as a prediction."),
            ("wellness", "Separate symbolism from health decisions", "Use the reading as a mindfulness prompt and keep health choices based on symptoms, evidence, and qualified professional guidance."),
        ]
        generated = []
        for category, title, description in templates:
            if context:
                description += " Personalization context is available from your completed profile and reading history."
            rec = Recommendation(user_id=user_id, category=category, title=title, description=description, is_completed=False)
            db.add(rec)
            generated.append(rec)
        db.commit()
        for rec in generated:
            db.refresh(rec)
        return generated

    @staticmethod
    def generate_combined_recommendations(db: Session, user_id: int, palm_data: dict, tarot_cards: list, focus_intent: str = "General Growth") -> list:
        if not palm_data or not tarot_cards:
            raise ValueError("Combined recommendations require actual palm and tarot results.")
        card_names = ", ".join(str(c.get("card_name")) for c in tarot_cards if c.get("card_name"))
        head = palm_data.get("head_line_conf", 0)
        fate = palm_data.get("fate_line_conf", 0)
        definitions = [
            ("career", "Turn the focus into a concrete milestone", f"Use the Head Line detection confidence ({head}%) and the {card_names} card themes as reflection prompts while defining one measurable next step for '{focus_intent}'."),
            ("relationship", "Make space for honest communication", f"Reflect on the Heart Line observation ({palm_data.get('heart_line_conf', 0)}%) and the spread themes before choosing a communication action that respects everyone's boundaries."),
            ("growth", "Review the reading before acting", "Write down what the spread suggests, what your real-world evidence says, and the action you control. Revisit the comparison before making a major decision."),
            ("wellness", "Use vitality symbolism mindfully", f"Treat the Life Line observation ({palm_data.get('life_line_conf', 0)}%) as symbolic only. Build sustainable rest and self-care habits without using the reading as a medical assessment."),
        ]
        rows = []
        for category, title, description in definitions:
            row = Recommendation(user_id=user_id, category=category, title=title, description=description, is_completed=False)
            db.add(row); rows.append(row)
        db.commit()
        for row in rows: db.refresh(row)
        return rows
