import os
from openai import OpenAI
from backend.app.config.config import settings

class AIInterpretationService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def generate_palm_interpretation(self, user_name: str, goals: list, palm_data: dict) -> dict:
        prompt = f"""
        User Name: {user_name}
        Spiritual Goals: {', '.join(goals)}
        Palm Shape: {palm_data.get('palm_shape')}
        Finger Structure: {palm_data.get('finger_structure')}
        Line Confidences:
          - Life Line: {palm_data.get('life_line_conf')}%
          - Head Line: {palm_data.get('head_line_conf')}%
          - Heart Line: {palm_data.get('heart_line_conf')}%
          - Fate Line: {palm_data.get('fate_line_conf')}%

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
                        {"role": "system", "content": "You are a professional spiritual guide specializing in palmistry and tarot. You provide symbolic, self-reflective interpretations and always use non-predictive language."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                import json
                result = json.loads(response.choices[0].message.content)
                return {
                    "summary": result.get("summary", ""),
                    "detailed_insight": result.get("detailed_insight", ""),
                    "safety_disclaimer": "This assessment is an AI-generated symbolic analysis intended for self-reflection and entertainment. It does not constitute medical, legal, or financial advice."
                }
            except Exception as e:
                print(f"OpenAI API call failed: {e}. Falling back to demo mode.")

        # Deterministic Fallback Mode (Demo Mode)
        shape = palm_data.get('palm_shape', 'Earth Hand')
        fingers = palm_data.get('finger_structure', 'Square Structure')
        
        summary = f"Your {shape} aligned with a {fingers} indicates a strong grounding in practical actions and reflective thinking."
        detailed_insight = (
            f"Greetings, {user_name}. The OpenCV model detected high line structures. "
            f"Your Life Line sharpness ({palm_data.get('life_line_conf')}%) suggests a high capacity for resilience and adaptation. "
            f"The Head Line coordinate trace ({palm_data.get('head_line_conf')}%) indicates clear cognitive decision-making channels. "
            f"Your Heart Line ({palm_data.get('heart_line_conf')}%) suggests a focus on empathy, balance, and maintaining healthy boundaries. "
            f"Finally, your Fate Line confidence ({palm_data.get('fate_line_conf')}%) points toward active adjustments in your long-term goal alignment, "
            f"matching your target goals of {', '.join(goals).lower() or 'self-reflection'}."
        )

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": "This assessment is an AI-generated symbolic analysis intended for self-reflection and entertainment. It does not constitute medical, legal, or financial advice."
        }

    def generate_tarot_interpretation(self, user_name: str, intent: str, cards_drawn: list) -> dict:
        cards_desc = []
        for c in cards_drawn:
            card_obj = c["card"]
            pos = c["position_name"]
            rev = "reversed" if c["is_reversed"] else "upright"
            cards_desc.append(f"Card '{card_obj.name}' in position '{pos}' ({rev})")

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
                        {"role": "system", "content": "You are a professional spiritual guide specializing in palmistry and tarot. You provide symbolic, self-reflective interpretations and always use non-predictive language."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                import json
                result = json.loads(response.choices[0].message.content)
                return {
                    "summary": result.get("summary", ""),
                    "detailed_insight": result.get("detailed_insight", ""),
                    "safety_disclaimer": "This tarot divination is an AI-generated symbolic reading intended for self-reflection. It is not professional counseling or financial guidance."
                }
            except Exception as e:
                print(f"OpenAI API call failed: {e}. Falling back to demo mode.")

        # Deterministic Fallback Mode (Demo Mode)
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
            f"Consider exploring how these symbolic dynamics map to your current actions and choices."
        )

        return {
            "summary": summary,
            "detailed_insight": detailed_insight,
            "safety_disclaimer": "This tarot divination is an AI-generated symbolic reading intended for self-reflection. It is not professional counseling or financial guidance."
        }

ai_interpretation_service = AIInterpretationService()
