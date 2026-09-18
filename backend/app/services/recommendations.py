from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.sql_models import Recommendation, UserProfile

ZODIAC_ELEMENTS = {
    "Aries": ("Fire", "Mars", "Pioneering leadership & swift execution"),
    "Leo": ("Fire", "Sun", "Creative magnetism & confident mentorship"),
    "Sagittarius": ("Fire", "Jupiter", "Philosophical expansion & adventurous vision"),
    "Taurus": ("Earth", "Venus", "Grounded endurance & material stewardship"),
    "Virgo": ("Earth", "Mercury", "Analytical discernment & holistic mastery"),
    "Capricorn": ("Earth", "Saturn", "Structural ambition & disciplined legacy"),
    "Gemini": ("Air", "Mercury", "Intellectual versatility & communicative synergy"),
    "Libra": ("Air", "Venus", "Harmonious equilibrium & strategic diplomacy"),
    "Aquarius": ("Air", "Uranus", "Visionary innovation & humanitarian impact"),
    "Cancer": ("Water", "Moon", "Intuitive sanctuary & heartfelt emotional depth"),
    "Scorpio": ("Water", "Pluto", "Transformative power & psychological insight"),
    "Pisces": ("Water", "Neptune", "Mystical empathy & transcendent imagination"),
}


class RecommendationEngine:
    @staticmethod
    def _get_user_zodiac_info(db: Session, user_id: int):
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        prefs = (profile.preferences if profile and isinstance(profile.preferences, dict) else {}) or {}
        zodiac_name = prefs.get("zodiac") or "Scorpio"
        elem_info = ZODIAC_ELEMENTS.get(zodiac_name, ("Universal", "Cosmic", "Balanced evolution"))
        return zodiac_name, elem_info[0], elem_info[1], elem_info[2]

    @staticmethod
    def generate_recommendations(db: Session, user_id: int, goals: list, reading_context: str) -> list:
        """Create practical recommendations from the user's actual goals, context, and Zodiac sign."""
        goal_text = ", ".join(str(g) for g in (goals or [])) or "personal reflection"
        zodiac_name, element, planet, quality = RecommendationEngine._get_user_zodiac_info(db, user_id)
        templates = [
            ("career", f"Channel {zodiac_name} Strengths into Measurable Goals", f"As a {zodiac_name} ({element} sign ruled by {planet}), align your career momentum with {goal_text}. Focus on {quality} for concrete outcomes."),
            ("relationship", f"Honor {zodiac_name} Emotional Boundaries", f"Apply {zodiac_name} emotional wisdom in daily dialogue. Maintain transparent communication while honoring mutual autonomy and respect."),
            ("growth", f"{zodiac_name} Reflective Log & Spiritual Practice", f"Record daily observations keyed to your {element} sign traits. Reflect on how your focus on {goal_text} develops over a weekly cycle."),
            ("wellness", f"{element} Energy Balance & Mindful Pacing", f"Nurture your physical constitution through {element}-aligning grounding rituals and adequate restorative rest."),
        ]
        generated = []
        for category, title, description in templates:
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
        heart = palm_data.get("heart_line_conf", 0)
        life = palm_data.get("life_line_conf", 0)
        zodiac_name, element, planet, quality = RecommendationEngine._get_user_zodiac_info(db, user_id)

        definitions = [
            ("career", f"{zodiac_name} Career Milestone: Execute Strategic Next Steps", f"Harness your {head}% Head Line clarity alongside your {zodiac_name} ({element}) drive for {quality}. Let {card_names} inspire a 30-day expansion milestone around '{focus_intent}'."),
            ("relationship", f"Harmonize {zodiac_name} Heart Line Resilience", f"With a {heart}% Heart Line resonance, balance {zodiac_name}'s relational depth with compassionate boundaries and open communication."),
            ("growth", f"{zodiac_name} Spiritual Alignment Ritual", f"Channel the archetypes of {card_names} through {zodiac_name}'s ruling guide ({planet}) into a structured weekly reflection ritual."),
            ("wellness", f"{element} Energy Rest & Vitality Pacing", f"Your {life}% Life Line indicator suggests aligning physical rhythms with {element} element grounding practices to maintain peak spiritual vitality."),
        ]
        rows = []
        for category, title, description in definitions:
            row = Recommendation(user_id=user_id, category=category, title=title, description=description, is_completed=False)
            db.add(row)
            rows.append(row)
        db.commit()
        for row in rows:
            db.refresh(row)
        return rows
