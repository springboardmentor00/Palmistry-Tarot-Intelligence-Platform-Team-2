import random
from sqlalchemy.orm import Session
from backend.app.models.sql_models import TarotCard

VALID_SPREADS = {"single": 1, "three": 3, "celtic": 10}


class InvalidSpreadError(ValueError):
    """Raised when a requested spread_name is not one of the platform's
    supported spreads."""
    pass


class TarotDeckService:
    @staticmethod
    def seed_tarot_deck(db: Session):
        # Check if already seeded
        if db.query(TarotCard).count() >= 78:
            return

        major_arcana = [
            ("The Fool", ["New Beginnings", "Faith", "Spontaneity", "Wonder"]),
            ("The Magician", ["Manifestation", "Willpower", "Creation", "Skill"]),
            ("The High Priestess", ["Intuition", "Sacred Knowledge", "Divine Feminine", "Mystery"]),
            ("The Empress", ["Fecundity", "Motherhood", "Nature", "Abundance"]),
            ("The Emperor", ["Authority", "Structure", "Control", "Solidarity"]),
            ("The Hierophant", ["Tradition", "Spiritual Wisdom", "Conformity", "Mentorship"]),
            ("The Lovers", ["Harmony", "Relationships", "Choices", "Alignment"]),
            ("The Chariot", ["Control", "Willpower", "Success", "Action"]),
            ("Strength", ["Courage", "Influence", "Compassion", "Inner Power"]),
            ("The Hermit", ["Contemplation", "Solitude", "Search for Truth", "Inner Guidance"]),
            ("Wheel of Fortune", ["Change", "Cycles", "Luck", "Destiny"]),
            ("Justice", ["Justice", "Karma", "Truth", "Fairness"]),
            ("The Hanged Man", ["Perspective", "Surrender", "Sacrifice", "Letting Go"]),
            ("Death", ["Transformation", "Endings", "Transitions", "Rebirth"]),
            ("Temperance", ["Balance", "Moderation", "Patience", "Harmony"]),
            ("The Devil", ["Attachment", "Addiction", "Shadow Self", "Materialism"]),
            ("The Tower", ["Sudden Change", "Revelation", "Chaos", "Breakthrough"]),
            ("The Star", ["Hope", "Faith", "Purpose", "Renewal"]),
            ("The Moon", ["Illusion", "Fear", "Anxiety", "Subconscious"]),
            ("The Sun", ["Joy", "Success", "Celebration", "Vitality"]),
            ("Judgement", ["Reflection", "Reckoning", "Awakening", "Absolution"]),
            ("The World", ["Completion", "Integration", "Travel", "Accomplishment"])
        ]

        suits = ["Cups", "Wands", "Swords", "Pentacles"]
        court_cards = ["Page", "Knight", "Queen", "King"]
        pip_cards = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]

        cards_to_insert = []

        # 1. Seed Major Arcana
        for idx, (name, keywords) in enumerate(major_arcana):
            card = TarotCard(
                id=idx + 1,
                name=name,
                arcana="Major",
                suit="None",
                keywords=keywords,
                meaning_upright=f"The presence of {name} upright indicates alignment with core themes of {', '.join(keywords[:2]).lower()}.",
                meaning_reversed=f"The presence of {name} reversed indicates resistance to or imbalances in {', '.join(keywords[2:]).lower()}.",
                personality_meaning=f"You are embodying the spiritual archetype of {name}, signaling a strong pull toward deep self-reflection.",
                relationship_meaning=f"In relationships, {name} suggests a period of intense learning and emotional exploration.",
                career_meaning=f"Career-wise, {name} points to a period of alignment where your tasks need to match your values.",
                finance_meaning=f"Finance themes revolve around mindful allocation and understanding values beyond material gains.",
                personal_growth_meaning=f"For personal growth, {name} asks you to step back and evaluate active cycles.",
                symbolism=f"Rich in historical esoteric symbolism, {name} represents a major key in the fool's lifecycle journey."
            )
            cards_to_insert.append(card)

        # 2. Seed Minor Arcana
        card_id = 23
        for suit in suits:
            # Seed Pips (Ace to Ten)
            for idx, pip in enumerate(pip_cards):
                val_name = f"{pip} of {suit}"
                keywords = [suit[:-1], pip, "Cycle Step", "Energy"]
                card = TarotCard(
                    id=card_id,
                    name=val_name,
                    arcana="Minor",
                    suit=suit,
                    keywords=keywords,
                    meaning_upright=f"Upright {val_name} points to the direct manifestation of {suit.lower()} energy in your immediate environment.",
                    meaning_reversed=f"Reversed {val_name} suggests blocks or internal conflicts surrounding your {suit.lower()} focus.",
                    personality_meaning=f"This card represents active, practical energies involving {suit.lower()} themes.",
                    relationship_meaning=f"Expect changes or communications relating to {suit.lower()} traits in your relationships.",
                    career_meaning=f"Professional cycles are strongly colored by the structural qualities of {pip}.",
                    finance_meaning=f"Financial assessments call for balance and review of your current material investments.",
                    personal_growth_meaning=f"Growth is achieved by looking at the lessons of the number {idx+1} in this suit.",
                    symbolism=f"Illustrates the numerical progression of the element representing {suit.lower()}."
                )
                cards_to_insert.append(card)
                card_id += 1

            # Seed Court Cards
            for court in court_cards:
                val_name = f"{court} of {suit}"
                keywords = [suit[:-1], court, "Persona", "Message"]
                card = TarotCard(
                    id=card_id,
                    name=val_name,
                    arcana="Minor",
                    suit=suit,
                    keywords=keywords,
                    meaning_upright=f"Upright {val_name} represents a messenger, person, or attitude carrying the qualities of the {suit.lower()} element.",
                    meaning_reversed=f"Reversed {val_name} points to developmental blocks, maturity gaps, or unstable moods in your circle.",
                    personality_meaning=f"You are taking on the role of the {court} of {suit}, balancing action and planning.",
                    relationship_meaning=f"A person embodying the traits of the {court} of {suit} may enter or impact your dynamics.",
                    career_meaning=f"Apply the professional discipline of the {court} to your active task plans.",
                    finance_meaning=f"Look at finance from a long-range strategic viewpoint, avoiding short-term impulses.",
                    personal_growth_meaning=f"Learn to balance the intellectual or emotional demands of this court figure.",
                    symbolism=f"Depicts the personification of the elemental lessons of the suit of {suit.lower()}."
                )
                cards_to_insert.append(card)
                card_id += 1

        db.add_all(cards_to_insert)
        db.commit()

    @staticmethod
    def draw_spread(db: Session, spread_name: str) -> list:
        if spread_name not in VALID_SPREADS:
            raise InvalidSpreadError(
                f"Unsupported spread '{spread_name}'. Supported spreads are: {', '.join(VALID_SPREADS.keys())}."
            )

        count = VALID_SPREADS[spread_name]

        # Get all card ids
        all_cards = db.query(TarotCard).all()
        if not all_cards:
            raise ValueError("Tarot deck is not seeded.")
        if len(all_cards) < count:
            raise ValueError(
                f"Tarot deck has only {len(all_cards)} cards seeded; cannot draw a {spread_name} spread of {count}."
            )

        drawn_cards = random.sample(all_cards, count)

        if spread_name == "single":
            positions = ["Core Focus"]
        elif spread_name == "three":
            positions = ["Past", "Present", "Future"]
        else:  # celtic
            positions = [
                "1. Present Foundation",
                "2. Immediate Challenge",
                "3. Subconscious Grounding",
                "4. Distant History",
                "5. Conscious Focus",
                "6. Immediate Horizon",
                "7. Personal Power",
                "8. Environmental Influence",
                "9. Hopes & Fears",
                "10. Ultimate Synthesis"
            ]

        results = []
        for idx, card in enumerate(drawn_cards):
            # Guard against any malformed card record making it into a reading.
            if card is None or not card.name or not card.meaning_upright or not card.meaning_reversed:
                raise ValueError("Encountered an invalid card record while drawing the spread.")
            is_reversed = random.random() > 0.75  # 25% chance reversed
            results.append({
                "card": card,
                "position_name": positions[idx],
                "is_reversed": is_reversed
            })

        return results
