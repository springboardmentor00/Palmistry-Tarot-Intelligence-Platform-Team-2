import json
import os
from openai import OpenAI
from backend.app.config.config import settings


class AIInterpretationService:
    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")

    def _get_card_attr(self, card_obj, attr: str, default: str = ""):
        """Helper to extract attributes safely from either SQLAlchemy models or dicts."""
        if isinstance(card_obj, dict):
            return card_obj.get(attr, default)
        return getattr(card_obj, attr, default)

    def generate_palm_interpretation(self, user_name: str, goals: list, palm_data: dict) -> dict:
        safe_goals = goals if isinstance(goals, list) and goals else ["Self-Reflection"]
        goals_str = ", ".join(safe_goals)

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

        Generate a professional, spiritual palmistry reading using self-reflective, non-guaranteed language.
        Do not state predictions as definite facts. Do not make medical diagnoses.
        Format the response in JSON with:
        {{
            "summary": "Short 1-2 sentence overview",
            "detailed_insight": "A comprehensive reflection based on the shapes and confidence values."
        }}
        """

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a professional spiritual guide specializing in palmistry and tarot. "
                                "You provide symbolic, self-reflective interpretations and always use non-predictive language."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                result = json.loads(response.choices[0].message.content)
                return {
                    "summary": result.get("summary", ""),
                    "detailed_insight": result.get("detailed_insight", ""),
                    "safety_disclaimer": (
                        "This assessment is an AI-generated symbolic analysis intended for self-reflection "
                        "and entertainment. It does not constitute medical, legal, or financial advice."
                    ),
                }
            except Exception as e:
                print(f"OpenAI API call failed for Palm interpretation: {e}. Falling back to demo mode.")

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

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": (
                "This assessment is an AI-generated symbolic analysis intended for self-reflection "
                "and entertainment. It does not constitute medical, legal, or financial advice."
            ),
        }

    def generate_tarot_interpretation(self, user_name: str, intent: str, cards_drawn: list) -> dict:
        cards_desc = []
        for c in cards_drawn:
            card_obj = c.get("card")
            card_name = self._get_card_attr(card_obj, "name", "Unknown Card")
            pos = c.get("position_name", "General")
            rev = "reversed" if c.get("is_reversed") else "upright"
            cards_desc.append(f"Card '{card_name}' in position '{pos}' ({rev})")

        prompt = f"""
        User Name: {user_name}
        Intention Focus: {intent}
        Cards Drawn:
        {', '.join(cards_desc)}

        Generate a professional, cohesive tarot spread reading synthesizing the relationship between cards.
        Use self-reflective, symbolic, non-guaranteed language.
        Do not state predictions as definite facts. Do not make medical diagnoses.
        Format the response in JSON with:
        {{
            "summary": "Short 1-2 sentence overview",
            "detailed_insight": "A comprehensive reflection based on the layout dynamics."
        }}
        """

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a professional spiritual guide specializing in palmistry and tarot. "
                                "You provide symbolic, self-reflective interpretations and always use non-predictive language."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                result = json.loads(response.choices[0].message.content)
                return {
                    "summary": result.get("summary", ""),
                    "detailed_insight": result.get("detailed_insight", ""),
                    "safety_disclaimer": (
                        "This tarot divination is an AI-generated symbolic reading intended for self-reflection. "
                        "It is not professional counseling or financial guidance."
                    ),
                }
            except Exception as e:
                print(f"OpenAI API call failed for Tarot interpretation: {e}. Falling back to demo mode.")

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

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": (
                "This tarot divination is an AI-generated symbolic reading intended for self-reflection. "
                "It is not professional counseling or financial guidance."
            ),
        }

    def synthesize_readings(
        self,
        user_name: str,
        goals: list,
        palm_data: dict,
        tarot_intent: str,
        cards_drawn: list,
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

        Synthesize these into a unified report. Format response in JSON with:
        {{
            "summary": "Overview bridging palm traits with tarot cards",
            "palm_insights": "Analysis of palm geometry & line metrics",
            "tarot_insights": "Analysis of tarot cards drawn",
            "unified_guidance": ["Action item 1", "Action item 2", "Action item 3"]
        }}
        """

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a master spiritual guide specializing in multi-modal synthesis of palmistry "
                                "and tarot. Use symbolic, non-predictive language."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                result = json.loads(response.choices[0].message.content)
                result["safety_disclaimer"] = (
                    "This synthesis is an AI-generated symbolic analysis intended for self-reflection "
                    "and entertainment. It does not constitute medical, legal, or financial advice."
                )
                return result
            except Exception as e:
                print(f"OpenAI API call failed for synthesis: {e}. Falling back to demo mode.")

        # Fallback Mode
        return {
            "summary": (
                f"For {user_name}, physical indicators from your {palm_data.get('palm_shape', 'Earth Hand')} "
                f"harmonize with the symbolic cards drawn for focus area '{tarot_intent or 'Self-Reflection'}'."
            ),
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
                "Maintain healthy emotional boundaries."
            ],
            "safety_disclaimer": (
                "This synthesis is an AI-generated symbolic analysis intended for self-reflection "
                "and entertainment. It does not constitute medical, legal, or financial advice."
            ),
        }


ai_interpretation_service = AIInterpretationService()
