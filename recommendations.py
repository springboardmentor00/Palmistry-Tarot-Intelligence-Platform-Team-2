import os
import json
from typing import List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from backend.app.models.sql_models import Recommendation


# 1. Pydantic Schemas for Gemini Structured Output
class SingleRecommendation(BaseModel):
    title: str = Field(..., description="Actionable title of the recommendation")
    description: str = Field(..., description="2-3 sentence personalized advice incorporating personality traits, life trends, and specific reading insights")
    category: str = Field(..., description="One of: 'career', 'relationship', or 'growth'")

class RecommendationListSchema(BaseModel):
    recommendations: List[SingleRecommendation]


class RecommendationEngine:
    @staticmethod
    def generate_recommendations(db: Session, user_id: int, goals: list, reading_context: str) -> list:
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Fallback to default static generation if API key is not configured
        if not api_key:
            return RecommendationEngine._generate_fallback(db, user_id)

        try:
            client = genai.Client(api_key=api_key)

            # Enhanced prompt incorporating personality, life trends, AI insights, and domain alignment
            prompt = f"""
            You are an expert AI Life & Growth Engine. Your task is to analyze user reading data (palmistry, tarot, astrology) along with core personality traits and active life trends to generate actionable personal recommendations.

            USER INPUT CONTEXT:
            - Active Life Goals: {', '.join(goals) if goals else 'General personal development and life balance'}
            - Personality, Life Trends & Reading Context: {reading_context}

            TASK INSTRUCTIONS:
            1. Analyze the context to extract key personality strengths, behavioral patterns, current life trends, and specific reading markers (e.g., palm line qualities, tarot card themes).
            2. Generate 3 to 5 highly practical, specific recommendations tailored directly to the user's situation.
            3. Ensure the recommendations cover the following critical life domains:
               - Career & Ambition (aligning skills, focus, and work decisions)
               - Relationships & Emotional Boundaries (communication, empathy, interpersonal dynamics)
               - Personal Growth & Self-Reflection (mindfulness, habits, self-development)
               - Goal Alignment (action steps connecting immediate choices to long-term goals)
            4. Explicitly weave together AI insights from reading context, personal traits, and life trends inside each advice description.
            """

            # Request structured JSON matching our Pydantic Schema
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RecommendationListSchema,
                    temperature=0.7,
                )
            )

            # Parse AI response
            parsed_data = json.loads(response.text)
            rec_items = parsed_data.get("recommendations", [])

            generated = []
            for item in rec_items:
                rec = Recommendation(
                    user_id=user_id,
                    category=item.get("category", "growth").lower(),
                    title=item.get("title", "Mindful Action"),
                    description=item.get("description", ""),
                    is_completed=False
                )
                db.add(rec)
                generated.append(rec)

            db.commit()
            return generated

        except Exception as e:
            db.rollback()
            # Fallback gracefully to database insertion if API call fails
            return RecommendationEngine._generate_fallback(db, user_id)

    @staticmethod
    def _generate_fallback(db: Session, user_id: int) -> list:
        """Fallback method in case API call fails or key is missing."""
        fallback_rec = Recommendation(
            user_id=user_id,
            category="growth",
            title="Mindful Reflection & Alignment",
            description="Take 10 minutes to write down your top priority for the week based on your latest reading, focus trends, and personal goals.",
            is_completed=False
        )
        db.add(fallback_rec)
        db.commit()
        return [fallback_rec]