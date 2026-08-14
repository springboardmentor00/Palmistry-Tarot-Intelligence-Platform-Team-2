import json
import logging
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError
from backend.app.config.config import settings

logger = logging.getLogger("aetheria.ai_service")

REQUEST_TIMEOUT_SECONDS = 20.0

PALM_SAFETY_DISCLAIMER = (
    "This assessment is an AI-generated symbolic analysis intended for self-reflection "
    "and entertainment. It does not constitute medical, legal, or financial advice."
)
TAROT_SAFETY_DISCLAIMER = (
    "This tarot divination is an AI-generated symbolic reading intended for self-reflection. "
    "It is not professional counseling or financial guidance."
)


class AIInterpretationService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, timeout=REQUEST_TIMEOUT_SECONDS)

    # ------------------------------------------------------------------ #
    # Response validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_ai_payload(raw_content: str) -> dict:
        """Parses and validates the AI JSON payload. Raises ValueError if the
        response is malformed or missing required fields, so callers fall
        back to deterministic demo output instead of returning garbage."""
        result = json.loads(raw_content)
        if not isinstance(result, dict):
            raise ValueError("AI response was not a JSON object.")
        summary = result.get("summary")
        detailed_insight = result.get("detailed_insight")
        if not summary or not isinstance(summary, str):
            raise ValueError("AI response missing a valid 'summary' field.")
        if not detailed_insight or not isinstance(detailed_insight, str):
            raise ValueError("AI response missing a valid 'detailed_insight' field.")
        return {"summary": summary.strip(), "detailed_insight": detailed_insight.strip()}

    # ------------------------------------------------------------------ #
    # Palm interpretation
    # ------------------------------------------------------------------ #
    def generate_palm_interpretation(self, user_name: str, goals: list, palm_data: dict) -> dict:
        if self.client:
            prompt = self._build_palm_prompt(user_name, goals, palm_data)
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional spiritual guide specializing in palmistry and tarot. You provide symbolic, self-reflective interpretations and always use non-predictive language."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                validated = self._validate_ai_payload(response.choices[0].message.content)
                return {
                    "summary": validated["summary"],
                    "detailed_insight": validated["detailed_insight"],
                    "safety_disclaimer": PALM_SAFETY_DISCLAIMER,
                    "source": "openai",
                }
            except APITimeoutError:
                logger.warning("OpenAI palm interpretation timed out; falling back to demo mode.")
            except (APIError, APIConnectionError) as e:
                logger.warning("OpenAI API error during palm interpretation (%s); falling back to demo mode.", e)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("OpenAI returned a malformed palm response (%s); falling back to demo mode.", e)
            except Exception:
                logger.exception("Unexpected error during palm AI interpretation; falling back to demo mode.")

        return self.fallback_palm_interpretation(user_name, goals, palm_data)

    def fallback_palm_interpretation(self, user_name: str, goals: list, palm_data: dict) -> dict:
        """Deterministic, clearly-labeled demo-mode interpretation. Used when
        no API key is configured, or when the live OpenAI call fails/returns
        malformed output. Never presented as a live AI result."""
        shape = palm_data.get('palm_shape', 'Earth Hand')
        fingers = palm_data.get('finger_structure', 'Square Structure')

        summary = f"Your {shape} aligned with a {fingers} indicates a strong grounding in practical actions and reflective thinking."
        detailed_insight = (
            f"Greetings, {user_name}. The computer-vision pipeline detected measurable line structures in your uploaded palm image. "
            f"Your Life Line signal ({palm_data.get('life_line_conf')}%) suggests a capacity for resilience and adaptation. "
            f"The Head Line signal ({palm_data.get('head_line_conf')}%) indicates cognitive decision-making channels. "
            f"Your Heart Line signal ({palm_data.get('heart_line_conf')}%) suggests a focus on empathy, balance, and maintaining healthy boundaries. "
            f"Your Fate Line signal ({palm_data.get('fate_line_conf')}%) points toward active adjustments in your long-term goal alignment, "
            f"and your Sun Line signal ({palm_data.get('sun_line_conf')}%) reflects creative and expressive potential, "
            f"matching your target goals of {', '.join(goals).lower() or 'self-reflection'}. "
            f"[Demo Mode: this narrative is generated deterministically from your CV feature scores, not a live OpenAI call.]"
        )

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": PALM_SAFETY_DISCLAIMER,
            "source": "demo_fallback",
        }

    def _build_palm_prompt(self, user_name: str, goals: list, palm_data: dict) -> str:
        return f"""
        User Name: {user_name}
        Spiritual Goals: {', '.join(goals)}
        Palm Shape: {palm_data.get('palm_shape')}
        Finger Structure: {palm_data.get('finger_structure')}
        Line Confidences (derived from real image analysis):
          - Life Line: {palm_data.get('life_line_conf')}%
          - Head Line: {palm_data.get('head_line_conf')}%
          - Heart Line: {palm_data.get('heart_line_conf')}%
          - Fate Line: {palm_data.get('fate_line_conf')}%
          - Sun Line: {palm_data.get('sun_line_conf')}%

        Generate a professional, spiritual palmistry reading using self-reflective, non-guaranteed language.
        Do not state predictions as definite facts. Do not make medical diagnoses.
        Format the response in JSON with:
        {{
            "summary": "Short 1-2 sentence overview",
            "detailed_insight": "A comprehensive reflection based on the shapes and confidence values."
        }}
        """

    # ------------------------------------------------------------------ #
    # Tarot interpretation
    # ------------------------------------------------------------------ #
    def generate_tarot_interpretation(self, user_name: str, intent: str, cards_drawn: list) -> dict:
        if self.client:
            prompt = self._build_tarot_prompt(user_name, intent, cards_drawn)
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional spiritual guide specializing in palmistry and tarot. You provide symbolic, self-reflective interpretations and always use non-predictive language."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                validated = self._validate_ai_payload(response.choices[0].message.content)
                return {
                    "summary": validated["summary"],
                    "detailed_insight": validated["detailed_insight"],
                    "safety_disclaimer": TAROT_SAFETY_DISCLAIMER,
                    "source": "openai",
                }
            except APITimeoutError:
                logger.warning("OpenAI tarot interpretation timed out; falling back to demo mode.")
            except (APIError, APIConnectionError) as e:
                logger.warning("OpenAI API error during tarot interpretation (%s); falling back to demo mode.", e)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("OpenAI returned a malformed tarot response (%s); falling back to demo mode.", e)
            except Exception:
                logger.exception("Unexpected error during tarot AI interpretation; falling back to demo mode.")

        return self.fallback_tarot_interpretation(user_name, intent, cards_drawn)

    def fallback_tarot_interpretation(self, user_name: str, intent: str, cards_drawn: list) -> dict:
        """Deterministic, clearly-labeled demo-mode interpretation."""
        card_names = [c["card"].name for c in cards_drawn]
        summary = f"The drawn spread highlights active influences from the {', '.join(card_names[:2])} archetype models."

        detail_lines = []
        for c in cards_drawn:
            card_name = c["card"].name
            pos = c["position_name"]
            orientation = "reversed" if c["is_reversed"] else "upright"
            meaning = c["card"].meaning_reversed if c["is_reversed"] else c["card"].meaning_upright
            detail_lines.append(f"In your position '{pos}', the card '{card_name}' ({orientation}) suggests: {meaning}")

        detailed_insight = (
            f"Dear {user_name}, for your focus area '{intent}', these cards reveal intersecting pathways. "
            f"{' '.join(detail_lines)} "
            f"Consider exploring how these symbolic dynamics map to your current actions and choices. "
            f"[Demo Mode: this narrative is generated deterministically from the drawn cards, not a live OpenAI call.]"
        )

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": TAROT_SAFETY_DISCLAIMER,
            "source": "demo_fallback",
        }

    def _build_tarot_prompt(self, user_name: str, intent: str, cards_drawn: list) -> str:
        cards_desc = []
        for c in cards_drawn:
            card_obj = c["card"]
            pos = c["position_name"]
            rev = "reversed" if c["is_reversed"] else "upright"
            cards_desc.append(f"Card '{card_obj.name}' in position '{pos}' ({rev})")

        return f"""
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


ai_interpretation_service = AIInterpretationService()
