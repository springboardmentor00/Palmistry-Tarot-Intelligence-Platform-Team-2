from typing import Dict, Any, List


class LifeTrendService:

    @staticmethod
    def calculate_trends(
        user_age_group: str,
        active_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Generates a personalized life-trend analysis using
        the user's age group and active goals.

        This is a symbolic/self-reflective analysis and
        does not make guaranteed predictions.
        """

        age_group = (user_age_group or "25-34").strip()
        goals = active_goals if isinstance(active_goals, list) else []

        normalized_goals = [
            str(goal).strip().lower()
            for goal in goals
            if goal
        ]

        # ---------------------------------------------------------
        # 1. Determine life-path stage
        # ---------------------------------------------------------

        age_stage_map = {
            "18-24": "Exploration & Foundation Phase",
            "25-34": "Growth & Direction Phase",
            "35-44": "Stability & Expansion Phase",
            "45-54": "Reflection & Leadership Phase",
            "55+": "Wisdom & Legacy Phase"
        }

        life_path_stage = age_stage_map.get(
            age_group,
            "Growth & Self-Discovery Phase"
        )

        # ---------------------------------------------------------
        # 2. Base trends
        # ---------------------------------------------------------

        trend_map = {
            "18-24": [
                "Building foundational skills",
                "Exploring career and personal identity",
                "Developing independence and confidence"
            ],
            "25-34": [
                "Strengthening career direction",
                "Building meaningful relationships",
                "Turning goals into consistent action"
            ],
            "35-44": [
                "Balancing achievement with personal fulfillment",
                "Strengthening long-term stability",
                "Expanding leadership and responsibility"
            ],
            "45-54": [
                "Re-evaluating priorities",
                "Using experience to guide important decisions",
                "Creating stronger personal and professional balance"
            ],
            "55+": [
                "Focusing on meaningful experiences",
                "Sharing knowledge and experience",
                "Prioritizing fulfillment, relationships and legacy"
            ]
        }

        current_trends = trend_map.get(
            age_group,
            [
                "Personal development",
                "Goal alignment",
                "Building sustainable habits"
            ]
        )

        # ---------------------------------------------------------
        # 3. Goal-based opportunities and challenges
        # ---------------------------------------------------------

        opportunities = []
        challenges = []

        if any(
            keyword in goal
            for goal in normalized_goals
            for keyword in ["career", "job", "professional", "skill"]
        ):
            opportunities.extend([
                "Opportunity to strengthen professional skills",
                "Potential to explore new career directions",
                "Favorable period for structured goal setting"
            ])

            challenges.extend([
                "Avoiding excessive comparison with others",
                "Maintaining consistency during career changes"
            ])

        if any(
            keyword in goal
            for goal in normalized_goals
            for keyword in ["relationship", "love", "family"]
        ):
            opportunities.extend([
                "Opportunity to improve communication",
                "Building stronger emotional connections",
                "Developing healthier relationship boundaries"
            ])

            challenges.extend([
                "Managing emotional expectations",
                "Maintaining personal boundaries"
            ])

        if any(
            keyword in goal
            for goal in normalized_goals
            for keyword in ["growth", "self", "personal", "reflection"]
        ):
            opportunities.extend([
                "Opportunity for deeper self-reflection",
                "Developing stronger self-awareness",
                "Creating sustainable personal-development habits"
            ])

            challenges.extend([
                "Avoiding overthinking",
                "Turning reflection into consistent action"
            ])

        if any(
            keyword in goal
            for goal in normalized_goals
            for keyword in ["finance", "money", "financial"]
        ):
            opportunities.extend([
                "Opportunity to improve financial planning",
                "Building stronger long-term financial habits"
            ])

            challenges.extend([
                "Avoiding impulsive financial decisions",
                "Maintaining realistic long-term goals"
            ])

        # ---------------------------------------------------------
        # 4. Default opportunities/challenges
        # ---------------------------------------------------------

        if not opportunities:
            opportunities = [
                "Opportunity to clarify personal priorities",
                "Developing new skills and experiences",
                "Creating consistent habits aligned with personal goals"
            ]

        if not challenges:
            challenges = [
                "Managing uncertainty during important decisions",
                "Maintaining consistency toward long-term goals",
                "Balancing personal priorities with external expectations"
            ]

        # ---------------------------------------------------------
        # 5. Growth potential
        # ---------------------------------------------------------

        goal_count = len(normalized_goals)

        if goal_count >= 3:
            growth_rating = "High"
        elif goal_count >= 1:
            growth_rating = "Moderate to High"
        else:
            growth_rating = "Moderate"

        # ---------------------------------------------------------
        # 6. Return structured life-trend analysis
        # ---------------------------------------------------------

        return {
            "life_path_stage": life_path_stage,
            "current_trends": current_trends,
            "upcoming_opportunities": opportunities,
            "forecasted_challenges": challenges,
            "growth_potential_rating": growth_rating,
            "active_goals": goals
        }