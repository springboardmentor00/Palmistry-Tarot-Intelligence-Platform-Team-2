import datetime
import json
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from sqlalchemy.orm import Session

from backend.app.config.config import settings
from backend.app.models.sql_models import PalmReading, TarotReading
from backend.app.services.life_trend import LifeTrendService
from backend.app.services.personality import PersonalityService


DISCLAIMER = (
    "This assessment is an AI-assisted symbolic interpretation intended for self-reflection and "
    "entertainment. It is not a medical, legal, financial, or professional prediction or advice."
)


class AIInterpretationService:
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY and OpenAI is not None:
            try:
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception:
                self.client = None

    @staticmethod
    def _card_attr(card_obj: Any, attr: str, default: str = "") -> str:
        if isinstance(card_obj, dict):
            return card_obj.get(attr, default)
        return getattr(card_obj, attr, default)

    def _call_openai_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return None

    def _context_block(
        self,
        age_group: Optional[str] = None,
        life_trend: Optional[dict] = None,
        personality: Optional[dict] = None,
    ) -> str:
        parts = []
        if age_group:
            parts.append(f"Life stage: {age_group}")
        if life_trend:
            parts.append(
                "Life-trend analysis: "
                f"stage={life_trend.get('life_path_stage')}; "
                f"trends={', '.join(life_trend.get('current_trends', []))}; "
                f"opportunities={', '.join(life_trend.get('upcoming_opportunities', []))}; "
                f"challenges={', '.join(life_trend.get('forecasted_challenges', []))}"
            )
        if personality:
            parts.append(
                "Personality profile: "
                f"traits={', '.join(personality.get('dominant_traits', []))}; "
                f"strengths={', '.join(personality.get('strengths', []))}; "
                f"growth_areas={', '.join(personality.get('weaknesses', []))}"
            )
        return "\n".join(parts)

    def generate_palm_interpretation(self, user_name: str, goals: list, palm_data: dict, *, age_group=None, life_trend=None, personality=None) -> dict:
        goals = goals if isinstance(goals, list) else []
        context = self._context_block(age_group, life_trend, personality)
        prompt = f"""User: {user_name}\nGoals: {', '.join(goals)}\nPalm data: {json.dumps(palm_data)}\n{context}\n\nReturn JSON with summary and detailed_insight. Use symbolic, non-predictive language."""
        result = self._call_openai_json(
            "You provide careful, symbolic palmistry reflections for self-reflection. Never present claims as scientific or certain.",
            prompt,
        )
        if result:
            return {"summary": result.get("summary", ""), "detailed_insight": result.get("detailed_insight", ""), "safety_disclaimer": DISCLAIMER}

        shape = palm_data.get("palm_shape", "an observed palm structure")
        fingers = palm_data.get("finger_structure", "the detected finger structure")
        line_values = [
            palm_data.get("life_line_conf", 0), palm_data.get("head_line_conf", 0),
            palm_data.get("heart_line_conf", 0), palm_data.get("fate_line_conf", 0),
        ]
        average = round(sum(line_values) / len(line_values), 1)
        summary = f"The observed {shape} and {fingers} provide a symbolic starting point for reflecting on your current goals and patterns."
        detail = (
            f"The computer-vision pipeline measured an average line-detection confidence of {average}%. "
            f"Life ({line_values[0]}%), Head ({line_values[1]}%), Heart ({line_values[2]}%), and Fate ({line_values[3]}%) "
            "can be used as reflective prompts rather than fixed statements about your future. "
            f"Consider how these themes relate to your stated goals: {', '.join(goals) if goals else 'self-reflection'}."
        )
        return {"summary": summary, "detailed_insight": detail, "safety_disclaimer": DISCLAIMER}

    def generate_tarot_interpretation(self, user_name: str, focus_intent: str, drawn: list, *, age_group=None, life_trend=None, personality=None) -> dict:
        cards = []
        for item in drawn:
            card = item["card"]
            cards.append({
                "name": self._card_attr(card, "name"),
                "position": item.get("position_name"),
                "orientation": "reversed" if item.get("is_reversed") else "upright",
                "meaning": self._card_attr(card, "meaning_reversed" if item.get("is_reversed") else "meaning_upright"),
            })
        prompt = f"""User: {user_name}\nFocus: {focus_intent}\nCards: {json.dumps(cards)}\n{self._context_block(age_group, life_trend, personality)}\n\nReturn JSON with summary and detailed_insight. Use symbolic, non-predictive language."""
        result = self._call_openai_json(
            "You provide careful, symbolic tarot reflections for self-reflection. Never present claims as certain predictions.",
            prompt,
        )
        if result:
            return {"summary": result.get("summary", ""), "detailed_insight": result.get("detailed_insight", ""), "safety_disclaimer": DISCLAIMER}

        if not cards:
            raise ValueError("A tarot spread must contain at least one card.")
        details = " ".join(f"{c['position']}: {c['name']} ({c['orientation']}) — {c['meaning']}" for c in cards)
        return {
            "summary": f"Your {focus_intent or 'general'} tarot reflection brings together {len(cards)} symbolic card themes.",
            "detailed_insight": f"{details} Treat the spread as a structured reflection on the question you brought to the session; the interpretation does not determine an outcome.",
            "safety_disclaimer": DISCLAIMER,
        }

    def _build_reading_history(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = []
        palms = db.query(PalmReading).filter(PalmReading.user_id == user_id).order_by(PalmReading.created_at.desc()).limit(25).all()
        for p in palms:
            history.append({"type": "palm", "shape": p.palm_shape, "finger_structure": p.finger_structure, "lines": [p.life_line_conf, p.head_line_conf, p.heart_line_conf, p.fate_line_conf]})
        tarot = db.query(TarotReading).filter(TarotReading.user_id == user_id).order_by(TarotReading.created_at.desc()).limit(25).all()
        for t in tarot:
            history.append({"type": "tarot", "spread": t.spread_name, "focus": t.focus_intent, "cards": [self._card_attr(c.card, "name") for c in (t.cards_drawn or [])]})
        return history

    def gather_context(self, db: Session, user) -> Dict[str, Any]:
        profile = getattr(user, "profile", None)
        goals = profile.goals if profile and profile.goals else []
        age_group = profile.age_group if profile and profile.age_group else None
        history = self._build_reading_history(db, user.id)
        life_trend = LifeTrendService.calculate_trends(age_group, goals) if age_group else LifeTrendService.calculate_trends("18-24", goals)
        personality = PersonalityService.analyze_profile(history) if history else None
        latest_palm = db.query(PalmReading).filter(PalmReading.user_id == user.id).order_by(PalmReading.created_at.desc()).first()
        latest_tarot = db.query(TarotReading).filter(TarotReading.user_id == user.id).order_by(TarotReading.created_at.desc()).first()
        return {
            "user_name": user.full_name,
            "goals": goals,
            "age_group": age_group,
            "life_trend": life_trend if history or goals else None,
            "personality": personality,
            "latest_palm": latest_palm,
            "latest_tarot": latest_tarot,
        }

    def generate_comprehensive_insight(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_name = context.get("user_name", "Seeker")
        palm = context.get("latest_palm")
        tarot = context.get("latest_tarot")
        personality = context.get("personality")
        life_trend = context.get("life_trend")
        if not palm and not tarot:
            raise ValueError("At least one completed palm or tarot reading is required.")

        palm_desc = f"Palm: shape={palm.palm_shape}, life={palm.life_line_conf}, head={palm.head_line_conf}, heart={palm.heart_line_conf}, fate={palm.fate_line_conf}" if palm else ""
        tarot_desc = ""
        if tarot:
            tarot_desc = "Tarot: " + ", ".join(
                f"{self._card_attr(c.card, 'name')} ({'reversed' if c.is_reversed else 'upright'})" for c in (tarot.cards_drawn or [])
            )
        prompt = f"""User: {user_name}\n{palm_desc}\n{tarot_desc}\nContext: {self._context_block(context.get('age_group'), life_trend, personality)}\nReturn JSON with summary and categories for personality, relationships, career, finance, wellness, personal_growth, life_opportunities."""
        result = self._call_openai_json("You synthesize palmistry and tarot into cautious symbolic self-reflection.", prompt)
        if result:
            categories = result.get("categories", {})
            return {"summary": result.get("summary", ""), "categories": categories, "sources_used": [s for s, present in (("palm_reading", bool(palm)), ("tarot_reading", bool(tarot)), ("life_trend_analysis", bool(life_trend)), ("personality_profile", bool(personality))) if present], "safety_disclaimer": DISCLAIMER, "generated_at": datetime.datetime.utcnow().isoformat()}

        categories = {
            "personality": personality.get("summary", "Reflect on the patterns visible in your completed readings.") if personality else "Use the completed reading as a prompt for self-observation.",
            "relationships": "Consider how the emotional themes in the reading connect with communication and personal boundaries.",
            "career": "Translate the reading's action-oriented themes into concrete goals and reviewable next steps.",
            "finance": "Use the reading as a reflection prompt and pair financial decisions with evidence-based planning.",
            "wellness": "Treat vitality-related symbolism as a self-care prompt, not as a health assessment.",
            "personal_growth": "Identify one insight from the completed reading and turn it into a small, observable habit.",
            "life_opportunities": "Review the opportunities and challenges in your life-trend context and choose one practical next action.",
        }
        sources = [s for s, present in (("palm_reading", bool(palm)), ("tarot_reading", bool(tarot)), ("life_trend_analysis", bool(life_trend)), ("personality_profile", bool(personality))) if present]
        return {"summary": f"A combined reflective overview has been prepared from {', '.join(sources)} for {user_name}.", "categories": categories, "sources_used": sources, "safety_disclaimer": DISCLAIMER, "generated_at": datetime.datetime.utcnow().isoformat()}

    def generate_combined_master_report(self, user_name: str, goals: list, palm_data: dict, tarot_cards: list, spread_name: str, focus_intent: str, *, age_group=None, life_trend=None, personality=None) -> dict:
        if not palm_data or not tarot_cards:
            raise ValueError("Combined analysis requires actual palm analysis data and a completed tarot spread.")
        line_avg = sum(float(palm_data.get(k, 0)) for k in ("life_line_conf", "head_line_conf", "heart_line_conf", "fate_line_conf", "sun_line_conf")) / 5
        major_count = sum(1 for c in tarot_cards if str(c.get("arcana", "")).lower() == "major")
        tarot_relevance = min(100.0, 75.0 + (major_count / len(tarot_cards)) * 20.0)
        personality_alignment = 0.0 if not personality else min(100.0, 55.0 + len(personality.get("dominant_traits", [])) * 8.0 + len(personality.get("strengths", [])) * 4.0)
        user_context = min(100.0, 50.0 + len(goals or []) * 10.0)
        reading_consistency = 50.0
        composite = round(line_avg * 0.30 + tarot_relevance * 0.25 + personality_alignment * 0.20 + user_context * 0.15 + reading_consistency * 0.10, 1)
        prompt = f"""User: {user_name}\nFocus: {focus_intent}\nPalm: {json.dumps(palm_data)}\nTarot: {json.dumps(tarot_cards)}\n{self._context_block(age_group, life_trend, personality)}\nReturn JSON with summary, composite_score and categories: executive_synthesis, mindset_cognition, career_ambition, love_relationships, health_vitality, destiny_milestones."""
        result = self._call_openai_json("You unify actual palm CV observations and actual tarot cards into cautious symbolic self-reflection.", prompt)
        if result:
            return {"summary": result.get("summary", ""), "composite_score": float(result.get("composite_score", composite)), "categories": result.get("categories", {}), "safety_disclaimer": DISCLAIMER, "generated_at": datetime.datetime.utcnow().isoformat()}
        card_names = ", ".join(c.get("card_name", "") for c in tarot_cards)
        return {
            "summary": f"The combined reading for {user_name} links observed palm-line measurements with the {spread_name} tarot spread around {focus_intent or 'general reflection'}.",
            "composite_score": composite,
            "categories": {
                "executive_synthesis": f"The observed palm metrics and the drawn cards ({card_names}) provide complementary prompts for reflection.",
                "mindset_cognition": f"The Head Line confidence ({palm_data.get('head_line_conf', 0)}%) can be used as a prompt to examine decision-making habits alongside the card themes.",
                "career_ambition": f"The Fate Line confidence ({palm_data.get('fate_line_conf', 0)}%) and the tarot spread can frame a review of goals and practical next actions.",
                "love_relationships": f"The Heart Line confidence ({palm_data.get('heart_line_conf', 0)}%) offers a symbolic prompt around communication and boundaries.",
                "health_vitality": f"The Life Line confidence ({palm_data.get('life_line_conf', 0)}%) is treated only as symbolic reading data; health decisions should use qualified professional guidance.",
                "destiny_milestones": "Use the spread positions and your stated goals to identify milestones that are concrete, measurable, and within your control.",
            },
            "safety_disclaimer": DISCLAIMER,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }


ai_interpretation_service = AIInterpretationService()
