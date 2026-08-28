import json
import os
import datetime
from typing import Optional, List, Dict, Any

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.app.config.config import settings
from backend.app.services.life_trend import LifeTrendService
from backend.app.services.personality import PersonalityService
from backend.app.services.astrology.birth_chart_service import birth_chart_service


class AIInterpretationService:
    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _get_card_attr(self, card_obj, attr: str, default: str = ""):
        """Helper to extract attributes safely from either SQLAlchemy models or dicts."""
        if isinstance(card_obj, dict):
            return card_obj.get(attr, default)
        return getattr(card_obj, attr, default)

    def _call_openai_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        """Shared OpenAI JSON-mode call used by every interpretation method. Returns None on any failure."""
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI API call failed: {e}. Falling back to demo mode.")
            return None

    def _context_block(
        self,
        age_group: Optional[str] = None,
        life_trend: Optional[dict] = None,
        personality: Optional[dict] = None,
        birth_chart_summary: Optional[str] = None,
    ) -> str:
        """Renders whatever extra personalization context is available into prompt text. Skips anything missing."""
        parts = []
        if age_group:
            parts.append(f"Life Stage / Age Group: {age_group}")
        if life_trend:
            parts.append(
                "Life-Trend Analysis:\n"
                f"  - Life Path Stage: {life_trend.get('life_path_stage', 'Unknown')}\n"
                f"  - Current Trends: {', '.join(life_trend.get('current_trends', []))}\n"
                f"  - Upcoming Opportunities: {', '.join(life_trend.get('upcoming_opportunities', []))}\n"
                f"  - Forecasted Challenges: {', '.join(life_trend.get('forecasted_challenges', []))}\n"
                f"  - Growth Potential: {life_trend.get('growth_potential_rating', 'Unknown')}"
            )
        if personality:
            parts.append(
                "Personality Profile:\n"
                f"  - Dominant Traits: {', '.join(personality.get('dominant_traits', []))}\n"
                f"  - Strengths: {', '.join(personality.get('strengths', []))}\n"
                f"  - Growth Areas: {', '.join(personality.get('weaknesses', []))}\n"
                f"  - Behavioral Insight: {personality.get('behavioral_insights', '')}"
            )
        if birth_chart_summary:
            parts.append(f"Birth Chart (Vedic & Western): {birth_chart_summary}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Palm interpretation (existing endpoint contract preserved)
    # ------------------------------------------------------------------
    def generate_palm_interpretation(
        self,
        user_name: str,
        goals: list,
        palm_data: dict,
        *,
        age_group: Optional[str] = None,
        life_trend: Optional[dict] = None,
        personality: Optional[dict] = None,
        birth_chart_summary: Optional[str] = None,
    ) -> dict:
        safe_goals = goals if isinstance(goals, list) and goals else ["Self-Reflection"]
        goals_str = ", ".join(safe_goals)
        extra_context = self._context_block(age_group, life_trend, personality, birth_chart_summary)

        prompt = f"""
        User Name: {user_name}
        Spiritual Goals: {goals_str}
        Palm Shape: {palm_data.get('palm_shape', 'Unknown')}
        Finger Structure: {palm_data.get('finger_structure', 'Unknown')}
        Line Confidences:
          - Life Line: {palm_data.get('life_line_conf', 0)}%
          - Head Line: {palm_data.get('head_line_conf', 0)}%
          - Heart Line: {palm_data.get('heart_line_conf', 0)}%
          - Fate Line: {palm_data.get('fate_line_conf', 0)}%

        {extra_context}

        Generate a professional, spiritual palmistry reading using self-reflective, non-guaranteed language.
        Weave in the additional personalization context above where it is present and relevant, so the
        reading feels specific to this person rather than generic.
        Do not state predictions as definite facts. Do not make medical diagnoses.
        Format the response in JSON with:
        {{
            "summary": "Short 1-2 sentence overview",
            "detailed_insight": "A comprehensive reflection based on the shapes and confidence values."
        }}
        """

        result = self._call_openai_json(
            "You are a professional spiritual guide specializing in palmistry and tarot. "
            "You provide symbolic, self-reflective interpretations and always use non-predictive language.",
            prompt,
        )
        if result:
            return {
                "summary": result.get("summary", ""),
                "detailed_insight": result.get("detailed_insight", ""),
                "safety_disclaimer": (
                    "This assessment is an AI-generated symbolic analysis intended for self-reflection "
                    "and entertainment. It does not constitute medical, legal, or financial advice."
                ),
            }

        # Deterministic Fallback Mode (Demo Mode)
        shape = palm_data.get("palm_shape", "Earth Hand")
        fingers = palm_data.get("finger_structure", "Square Structure")

        summary = (
            f"Your {shape} aligned with a {fingers} indicates a strong grounding in practical actions "
            "and reflective thinking."
        )
        detailed_insight = (
            f"Greetings, {user_name}. The OpenCV model detected high line structures. "
            f"Your Life Line sharpness ({palm_data.get('life_line_conf', 75)}%) suggests a high capacity for resilience and adaptation. "
            f"The Head Line coordinate trace ({palm_data.get('head_line_conf', 75)}%) indicates clear cognitive decision-making channels. "
            f"Your Heart Line ({palm_data.get('heart_line_conf', 75)}%) suggests a focus on empathy, balance, and maintaining healthy boundaries. "
            f"Finally, your Fate Line confidence ({palm_data.get('fate_line_conf', 70)}%) points toward active adjustments in your long-term goal alignment, "
            f"matching your target goals of {goals_str.lower()}."
        )
        if life_trend:
            detailed_insight += (
                f" This aligns with your current {life_trend.get('life_path_stage', 'life')} phase, "
                f"where {life_trend.get('current_trends', ['personal growth'])[0].lower()} is especially active."
            )
        if birth_chart_summary:
            detailed_insight += f" Your birth chart adds further texture: {birth_chart_summary}"

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": (
                "This assessment is an AI-generated symbolic analysis intended for self-reflection "
                "and entertainment. It does not constitute medical, legal, or financial advice."
            ),
        }

    # ------------------------------------------------------------------
    # Tarot interpretation (existing endpoint contract preserved)
    # ------------------------------------------------------------------
    def generate_tarot_interpretation(
        self,
        user_name: str,
        intent: str,
        cards_drawn: list,
        *,
        age_group: Optional[str] = None,
        life_trend: Optional[dict] = None,
        personality: Optional[dict] = None,
        birth_chart_summary: Optional[str] = None,
    ) -> dict:
        cards_desc = []
        for c in cards_drawn:
            card_obj = c.get("card")
            card_name = self._get_card_attr(card_obj, "name", "Unknown Card")
            pos = c.get("position_name", "General")
            rev = "reversed" if c.get("is_reversed") else "upright"
            cards_desc.append(f"Card '{card_name}' in position '{pos}' ({rev})")

        extra_context = self._context_block(age_group, life_trend, personality, birth_chart_summary)

        prompt = f"""
        User Name: {user_name}
        Intention Focus: {intent}
        Cards Drawn:
        {', '.join(cards_desc)}

        {extra_context}

        Generate a professional, cohesive tarot spread reading synthesizing the relationship between cards.
        Weave in the additional personalization context above where it is present and relevant.
        Use self-reflective, symbolic, non-guaranteed language.
        Do not state predictions as definite facts. Do not make medical diagnoses.
        Format the response in JSON with:
        {{
            "summary": "Short 1-2 sentence overview",
            "detailed_insight": "A comprehensive reflection based on the layout dynamics."
        }}
        """

        result = self._call_openai_json(
            "You are a professional spiritual guide specializing in palmistry and tarot. "
            "You provide symbolic, self-reflective interpretations and always use non-predictive language.",
            prompt,
        )
        if result:
            return {
                "summary": result.get("summary", ""),
                "detailed_insight": result.get("detailed_insight", ""),
                "safety_disclaimer": (
                    "This tarot divination is an AI-generated symbolic reading intended for self-reflection. "
                    "It is not professional counseling or financial guidance."
                ),
            }

        # Deterministic Fallback Mode (Demo Mode)
        card_names = [self._get_card_attr(c.get("card"), "name", "Card") for c in cards_drawn]
        first_two_names = ", ".join(card_names[:2]) if card_names else "drawn"
        summary = f"The drawn spread highlights active influences from the {first_two_names} archetype models."

        detail_lines = []
        for c in cards_drawn:
            card_obj = c.get("card")
            card_name = self._get_card_attr(card_obj, "name", "Card")
            pos = c.get("position_name", "General")
            is_rev = c.get("is_reversed", False)
            orientation = "reversed" if is_rev else "upright"

            meaning_attr = "meaning_reversed" if is_rev else "meaning_upright"
            meaning = self._get_card_attr(
                card_obj, meaning_attr, "represents inner transformation and symbolic growth."
            )
            detail_lines.append(
                f"In your position '{pos}', the card '{card_name}' ({orientation}) suggests: {meaning}"
            )

        detailed_insight = (
            f"Dear {user_name}, for your focus area '{intent or 'General Guidance'}', these cards reveal intersecting pathways. "
            f"{' '.join(detail_lines)} "
            "Consider exploring how these symbolic dynamics map to your current actions and choices."
        )
        if life_trend:
            detailed_insight += (
                f" These cards surface during your {life_trend.get('life_path_stage', 'current')} phase, "
                f"reinforcing the theme of {life_trend.get('current_trends', ['growth'])[0].lower()}."
            )
        if birth_chart_summary:
            detailed_insight += f" {birth_chart_summary}"

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": (
                "This tarot divination is an AI-generated symbolic reading intended for self-reflection. "
                "It is not professional counseling or financial guidance."
            ),
        }

    # ------------------------------------------------------------------
    # Palm + Tarot synthesis (existing method contract preserved)
    # ------------------------------------------------------------------
    def synthesize_readings(
        self,
        user_name: str,
        goals: list,
        palm_data: dict,
        tarot_intent: str,
        cards_drawn: list,
        *,
        age_group: Optional[str] = None,
        life_trend: Optional[dict] = None,
        personality: Optional[dict] = None,
        birth_chart_summary: Optional[str] = None,
    ) -> dict:
        """Combines palmistry features and tarot readings into a single holistic synthesis report."""
        cards_desc = []
        for c in cards_drawn:
            card_obj = c.get("card")
            card_name = self._get_card_attr(card_obj, "name", "Unknown Card")
            pos = c.get("position_name", "General")
            rev = "reversed" if c.get("is_reversed") else "upright"
            cards_desc.append(f"  - Card '{card_name}' in position '{pos}' ({rev})")

        goals_str = ", ".join(goals) if isinstance(goals, list) and goals else "Self-Reflection"
        cards_summary = "\n".join(cards_desc) if cards_desc else "No cards drawn."
        extra_context = self._context_block(age_group, life_trend, personality, birth_chart_summary)

        prompt = f"""
        User Name: {user_name}
        Spiritual Goals: {goals_str}

        Palmistry Features:
          - Shape: {palm_data.get('palm_shape', 'Unknown')}
          - Finger Structure: {palm_data.get('finger_structure', 'Unknown')}
          - Life Line Confidence: {palm_data.get('life_line_conf', 0)}%
          - Head Line Confidence: {palm_data.get('head_line_conf', 0)}%
          - Heart Line Confidence: {palm_data.get('heart_line_conf', 0)}%
          - Fate Line Confidence: {palm_data.get('fate_line_conf', 0)}%

        Tarot Context:
          - Intention Focus: {tarot_intent or 'General Reflection'}
          - Cards:
        {cards_summary}

        {extra_context}

        Synthesize all of the above (palm, tarot, and any life-trend / personality / birth-chart context
        provided) into one unified, coherent report — not disconnected observations. Format response in JSON with:
        {{
            "summary": "Overview bridging palm traits with tarot cards (and other context if present)",
            "palm_insights": "Analysis of palm geometry & line metrics",
            "tarot_insights": "Analysis of tarot cards drawn",
            "unified_guidance": ["Action item 1", "Action item 2", "Action item 3"]
        }}
        """

        result = self._call_openai_json(
            "You are a master spiritual guide specializing in multi-modal synthesis of palmistry, tarot, "
            "astrology, and life-trend context. Use symbolic, non-predictive language.",
            prompt,
        )
        if result:
            result["safety_disclaimer"] = (
                "This synthesis is an AI-generated symbolic analysis intended for self-reflection "
                "and entertainment. It does not constitute medical, legal, or financial advice."
            )
            return result

        # Fallback Mode
        summary = (
            f"For {user_name}, physical indicators from your {palm_data.get('palm_shape', 'Earth Hand')} "
            f"harmonize with the symbolic cards drawn for focus area '{tarot_intent or 'Self-Reflection'}'."
        )
        if life_trend:
            summary += f" Both align with your current {life_trend.get('life_path_stage', 'life')} phase."

        return {
            "summary": summary,
            "palm_insights": (
                f"Your Head line confidence ({palm_data.get('head_line_conf', 75)}%) shows focus, "
                f"and Heart line values ({palm_data.get('heart_line_conf', 75)}%) show emotional stability."
            ),
            "tarot_insights": (
                f"The spread featuring {len(cards_drawn)} cards highlights active growth cycles."
            ),
            "unified_guidance": [
                "Align daily focus with your core head-line cognitive strengths.",
                "Reflect on card position messages when making upcoming decisions.",
                "Maintain healthy emotional boundaries.",
            ],
            "safety_disclaimer": (
                "This synthesis is an AI-generated symbolic analysis intended for self-reflection "
                "and entertainment. It does not constitute medical, legal, or financial advice."
            ),
        }

    # ------------------------------------------------------------------
    # Context gathering — integrates life-trend, personality, and birth
    # chart data so downstream generation is properly personalized.
    # ------------------------------------------------------------------
    def _build_reading_history(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Builds a lightweight reading-history list (for PersonalityService) from this user's past readings."""
        from backend.app.models.sql_models import PalmReading, TarotReading, AIInterpretation

        history: List[Dict[str, Any]] = []

        palm_readings = (
            db.query(PalmReading).filter(PalmReading.user_id == user_id).all()
        )
        for p in palm_readings:
            ai_rec = (
                db.query(AIInterpretation)
                .filter(AIInterpretation.reading_type == "palm", AIInterpretation.reading_id == p.id)
                .first()
            )
            history.append({
                "type": "palm",
                "palm_shape": p.palm_shape,
                "summary": ai_rec.summary if ai_rec else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        tarot_readings = (
            db.query(TarotReading).filter(TarotReading.user_id == user_id).all()
        )
        for t in tarot_readings:
            ai_rec = (
                db.query(AIInterpretation)
                .filter(AIInterpretation.reading_type == "tarot", AIInterpretation.reading_id == t.id)
                .first()
            )
            history.append({
                "type": "tarot",
                "spread_name": t.spread_name,
                "focus_intent": t.focus_intent,
                "summary": ai_rec.summary if ai_rec else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })

        return history

    def gather_context(self, db: Session, user) -> Dict[str, Any]:
        """
        Assembles the full personalization context for a user: profile goals,
        life-trend analysis, personality profile, latest palm/tarot readings,
        and latest birth chart (if generated). This is the single place that
        integrates every available signal so generation methods stay simple.
        """
        from backend.app.models.sql_models import PalmReading, TarotReading, BirthChart

        profile = getattr(user, "profile", None)
        goals = profile.goals if profile and profile.goals else []
        age_group = profile.age_group if profile and profile.age_group else "25-34"

        life_trend_data = LifeTrendService.calculate_trends(age_group, goals)

        reading_history = self._build_reading_history(db, user.id)
        personality_data = PersonalityService.analyze_profile(reading_history)

        latest_palm = (
            db.query(PalmReading)
            .filter(PalmReading.user_id == user.id)
            .order_by(PalmReading.created_at.desc())
            .first()
        )
        latest_tarot = (
            db.query(TarotReading)
            .filter(TarotReading.user_id == user.id)
            .order_by(TarotReading.created_at.desc())
            .first()
        )
        latest_birth_chart = (
            db.query(BirthChart)
            .filter(BirthChart.user_id == user.id)
            .order_by(BirthChart.created_at.desc())
            .first()
        )

        birth_chart_summary = None
        birth_chart_data = None
        if latest_birth_chart:
            birth_chart_data = {
                "vedic_chart": latest_birth_chart.vedic_chart,
                "western_chart": latest_birth_chart.western_chart,
            }
            birth_chart_summary = birth_chart_service.summarize_for_ai(birth_chart_data)

        return {
            "user_name": getattr(user, "full_name", "Seeker"),
            "goals": goals,
            "age_group": age_group,
            "life_trend": life_trend_data,
            "personality": personality_data,
            "latest_palm": latest_palm,
            "latest_tarot": latest_tarot,
            "birth_chart_summary": birth_chart_summary,
            "birth_chart_data": birth_chart_data,
        }

    # ------------------------------------------------------------------
    # Comprehensive, category-based, multi-source insight
    # ------------------------------------------------------------------
    def generate_comprehensive_insight(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produces one coherent, categorized insight report (personality,
        relationships, career, finance, wellness, personal growth, life
        opportunities) from every signal available in `context` (as built
        by `gather_context`). Consumable directly by recommendation and
        dashboard layers.
        """
        user_name = context.get("user_name", "Seeker")
        goals = context.get("goals") or []
        life_trend = context.get("life_trend") or {}
        personality = context.get("personality") or {}
        latest_palm = context.get("latest_palm")
        latest_tarot = context.get("latest_tarot")
        birth_chart_summary = context.get("birth_chart_summary")

        sources_used = ["life_trend_analysis", "personality_profile"]
        if latest_palm:
            sources_used.append("palm_reading")
        if latest_tarot:
            sources_used.append("tarot_reading")
        if birth_chart_summary:
            sources_used.append("birth_chart")

        palm_desc = ""
        if latest_palm:
            palm_desc = (
                f"Latest Palm Reading: shape={latest_palm.palm_shape}, "
                f"fingers={latest_palm.finger_structure}, "
                f"life_line={latest_palm.life_line_conf}%, head_line={latest_palm.head_line_conf}%, "
                f"heart_line={latest_palm.heart_line_conf}%, fate_line={latest_palm.fate_line_conf}%"
            )

        tarot_desc = ""
        if latest_tarot:
            card_bits = []
            for c in getattr(latest_tarot, "cards_drawn", []) or []:
                card = getattr(c, "card", None)
                name = self._get_card_attr(card, "name", "Unknown Card")
                orientation = "reversed" if getattr(c, "is_reversed", False) else "upright"
                card_bits.append(f"{name} ({orientation}, {c.position_name})")
            tarot_desc = (
                f"Latest Tarot Reading: spread={latest_tarot.spread_name}, "
                f"focus={latest_tarot.focus_intent}, cards=[{', '.join(card_bits)}]"
            )

        extra_context = self._context_block(
            context.get("age_group"), life_trend, personality, birth_chart_summary
        )

        prompt = f"""
        User Name: {user_name}
        Stated Goals: {', '.join(goals) if goals else 'Self-Reflection'}

        {palm_desc}
        {tarot_desc}

        {extra_context}

        Using every available signal above, produce ONE coherent, personalized insight report —
        not disconnected observations. If a signal is missing, gracefully rely on the others.
        Use self-reflective, symbolic, non-guaranteed language. Do not state predictions as
        definite facts. Do not make medical, legal, or financial guarantees.

        Format the response in JSON with:
        {{
            "summary": "2-3 sentence overview weaving together whichever signals are present",
            "categories": {{
                "personality": "Insight text",
                "relationships": "Insight text",
                "career": "Insight text",
                "finance": "Insight text",
                "wellness": "Insight text",
                "personal_growth": "Insight text",
                "life_opportunities": "Insight text"
            }}
        }}
        """

        result = self._call_openai_json(
            "You are a master spiritual guide who synthesizes palmistry, tarot, astrology (Vedic and "
            "Western birth charts), and life-trend context into one coherent, categorized personal "
            "insight report. Always use symbolic, self-reflective, non-predictive language.",
            prompt,
        )
        if result:
            return {
                "summary": result.get("summary", ""),
                "categories": result.get("categories", {}),
                "sources_used": sources_used,
                "safety_disclaimer": (
                    "This report is an AI-generated symbolic analysis combining multiple readings for "
                    "self-reflection and entertainment. It does not constitute medical, legal, or "
                    "financial advice."
                ),
                "generated_at": datetime.datetime.utcnow().isoformat(),
            }

        return self._fallback_comprehensive_insight(context, sources_used)

    def _fallback_comprehensive_insight(
        self, context: Dict[str, Any], sources_used: List[str]
    ) -> Dict[str, Any]:
        """Deterministic (no-API) comprehensive insight, built by weaving together whatever context exists."""
        user_name = context.get("user_name", "Seeker")
        life_trend = context.get("life_trend") or {}
        personality = context.get("personality") or {}
        latest_palm = context.get("latest_palm")
        latest_tarot = context.get("latest_tarot")
        birth_chart_summary = context.get("birth_chart_summary")

        stage = life_trend.get("life_path_stage", "Growth Phase")
        trends = life_trend.get("current_trends", ["personal development"])
        opportunities = life_trend.get("upcoming_opportunities", [])
        challenges = life_trend.get("forecasted_challenges", [])
        traits = personality.get("dominant_traits", ["Reflective"])
        strengths = personality.get("strengths", [])
        weaknesses = personality.get("weaknesses", [])

        summary = (
            f"For {user_name}, currently in the '{stage}', "
            f"the combined signals point toward {trends[0].lower() if trends else 'steady personal growth'}."
        )
        if birth_chart_summary:
            summary += f" {birth_chart_summary}"

        def _first_or(seq, default):
            return seq[0] if seq else default

        categories = {
            "personality": (
                f"Your dominant traits — {', '.join(traits)} — {personality.get('behavioral_insights', '')} "
                + (f"Palm structure ({latest_palm.finger_structure}) reinforces this pattern." if latest_palm else "")
            ).strip(),
            "relationships": (
                f"{_first_or([o for o in opportunities if 'relationship' in o.lower() or 'communicat' in o.lower()], 'Focus on clear, honest communication in close relationships.')} "
                + (f"Heart Line confidence ({latest_palm.heart_line_conf}%) suggests your emotional openness." if latest_palm else "")
            ).strip(),
            "career": (
                f"{_first_or([o for o in opportunities if 'career' in o.lower() or 'professional' in o.lower() or 'skill' in o.lower()], 'A favorable window to clarify professional direction.')} "
                + (f"Fate Line confidence ({latest_palm.fate_line_conf}%) points to your long-term direction." if latest_palm else "")
            ).strip(),
            "finance": _first_or(
                [o for o in opportunities if "financ" in o.lower()],
                "Consider building consistent, sustainable financial habits during this phase.",
            ),
            "wellness": (
                f"{_first_or(challenges, 'Balance ambition with rest and consistent self-care.')} "
                + (f"Life Line confidence ({latest_palm.life_line_conf}%) reflects your baseline resilience." if latest_palm else "")
            ).strip(),
            "personal_growth": (
                f"Growth potential is rated '{life_trend.get('growth_potential_rating', 'Moderate')}'. "
                f"Strengths to lean on: {', '.join(strengths) if strengths else 'self-awareness and adaptability'}."
            ),
            "life_opportunities": (
                ", ".join(opportunities) if opportunities else "Stay open to unplanned opportunities for growth this cycle."
            ),
        }

        if latest_tarot:
            cards = getattr(latest_tarot, "cards_drawn", []) or []
            if cards:
                first_card = self._get_card_attr(getattr(cards[0], "card", None), "name", "")
                if first_card:
                    categories["personal_growth"] += f" The '{first_card}' card in your recent spread echoes this theme."

        return {
            "summary": summary,
            "categories": categories,
            "sources_used": sources_used,
            "safety_disclaimer": (
                "This report is an AI-generated symbolic analysis combining multiple readings for "
                "self-reflection and entertainment. It does not constitute medical, legal, or "
                "financial advice."
            ),
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }


ai_interpretation_service = AIInterpretationService()
