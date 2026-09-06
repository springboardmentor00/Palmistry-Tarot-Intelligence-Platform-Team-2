from typing import List, Dict, Any


class PersonalityService:
    @staticmethod
    def analyze_profile(
        reading_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personality profile from reading history.
        """

        reading_history = reading_history or []

        # Default personality traits
        dominant_traits = [
            "Intuitive",
            "Analytical",
            "Adaptable"
        ]

        strengths = [
            "Deep emotional awareness",
            "Strategic decision-making"
        ]

        weaknesses = [
            "Overthinking under pressure",
            "Hesitation during major shifts"
        ]

        behavioral_insights = (
            "Shows strong intuitive alignment but requires "
            "grounding and balanced decision-making."
        )

        development_recommendations = [
            "Practice confident decision-making.",
            "Develop emotional awareness.",
            "Maintain consistency when facing changes.",
            "Focus on personal growth and self-reflection."
        ]

        # Convert reading history into text for simple analysis
        history_text = str(reading_history).lower()

        # Add traits based on available reading information
        if any(
            word in history_text
            for word in ["creative", "intuition", "intuitive", "cups"]
        ):
            dominant_traits.append("Creative")

        if any(
            word in history_text
            for word in [
                "leadership",
                "confidence",
                "strength",
                "chariot"
            ]
        ):
            dominant_traits.append("Confident")

        if any(
            word in history_text
            for word in [
                "career",
                "work",
                "pentacles"
            ]
        ):
            behavioral_insights += (
                " Career and achievement appear to be "
                "important areas of focus."
            )

        if any(
            word in history_text
            for word in [
                "relationship",
                "love",
                "heart"
            ]
        ):
            behavioral_insights += (
                " Emotional relationships may strongly "
                "influence personal decisions."
            )

        # Remove duplicate traits
        dominant_traits = list(dict.fromkeys(dominant_traits))

        # Big Five scores
        traits_text = " ".join(dominant_traits).lower()

        big_five = {
            "openness": (
                82
                if "intuitive" in traits_text
                or "creative" in traits_text
                else 65
            ),
            "conscientiousness": (
                78
                if "analytical" in traits_text
                else 60
            ),
            "extraversion": (
                75
                if "confident" in traits_text
                else 52
            ),
            "agreeableness": (
                80
                if "emotional" in behavioral_insights.lower()
                else 65
            ),
            "emotional_stability": 70,
            "neuroticism": 45
        }

        # Personality type
        if "Intuitive" in dominant_traits:
            personality_type = "The Empathetic Healer"
        elif "Confident" in dominant_traits:
            personality_type = "The Confident Leader"
        elif "Analytical" in dominant_traits:
            personality_type = "The Balanced Strategist"
        else:
            personality_type = "The Reflective Explorer"

        # Short summary
        summary = (
            f"{personality_type} with dominant traits such as "
            f"{', '.join(dominant_traits[:3])}."
        )
        return {
            "dominant_traits": dominant_traits,
            "personality_traits": dominant_traits,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "behavioral_insights": behavioral_insights,
            "development_recommendations":
                development_recommendations,
            "personality_type": personality_type,
            "big_five": big_five,
            "summary": summary
        }

    @staticmethod
    def get_personality_profile(
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        M3 compatibility function.

        Accepts user data and generates a personality profile.
        """

        user_data = user_data or {}

        reading_history = user_data.get(
            "reading_history",
            []
        )

        # Support palm and tarot data if reading history
        # is not directly available.
        if not reading_history:

            palm_data = user_data.get(
                "palm_data",
                user_data.get("palm_result", {})
            )

            tarot_data = user_data.get(
                "tarot_data",
                user_data.get("tarot_result", {})
            )

            reading_history = [
                {
                    "palm_data": palm_data,
                    "tarot_data": tarot_data
                }
            ]

        return PersonalityService.analyze_profile(
            reading_history
        )