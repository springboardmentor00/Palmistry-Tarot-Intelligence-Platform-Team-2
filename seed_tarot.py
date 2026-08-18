from backend.app.database.postgres import SessionLocal, engine
# Explicit import of sql_models registers TarotCard onto Base.metadata
from backend.app.models.sql_models import Base, TarotCard

TAROT_CARDS_DATA = [
    {
        "name": "The Fool",
        "arcana": "Major",
        "suit": None,
        "keywords": ["Beginnings", "Innocence", "Spontaneity", "Free Spirit"],
        "meaning_upright": "New beginnings, potential, leaps of faith, and fresh optimism.",
        "meaning_reversed": "Recklessness, risk-taking, risk aversion, and delays.",
        "personality_meaning": "An adventurous soul who embraces the unknown without fear.",
        "relationship_meaning": "A fresh relationship or a exciting, uninhibited dynamic.",
        "career_meaning": "Starting a new career path, business venture, or creative project.",
        "finance_meaning": "Financial risk-taking; ensure calculated choices before spending.",
        "personal_growth_meaning": "Stepping out of your comfort zone and trusting the universe.",
        "symbolism": "A traveler standing at the edge of a cliff under a bright sun."
    },
    {
        "name": "The Magician",
        "arcana": "Major",
        "suit": None,
        "keywords": ["Manifestation", "Resourcefulness", "Power", "Action"],
        "meaning_upright": "Skill, focus, concentration, and turning vision into reality.",
        "meaning_reversed": "Illusion, unused talent, manipulation, and misdirection.",
        "personality_meaning": "A driven, charismatic individual capable of bringing ideas to life.",
        "relationship_meaning": "Active creation of deep connection; clear and open alignment.",
        "career_meaning": "Having all the tools necessary to achieve your career objectives.",
        "finance_meaning": "Taking proactive measures to build wealth and harness opportunities.",
        "personal_growth_meaning": "Recognizing your inherent power to shape your own reality.",
        "symbolism": "A figure with one hand pointed to heaven and one to earth."
    },
    {
        "name": "The High Priestess",
        "arcana": "Major",
        "suit": None,
        "keywords": ["Intuition", "Sacred Knowledge", "Divine Feminine", "Subconscious"],
        "meaning_upright": "Inner wisdom, mystery, intuition, and spiritual insight.",
        "meaning_reversed": "Secrets, disconnected intuition, superficiality, and withdrawal.",
        "personality_meaning": "An intuitive, reflective person tuned into subtle energies.",
        "relationship_meaning": "Unspoken emotional depth, mutual understanding, and patience.",
        "career_meaning": "Trusting your gut feelings regarding professional decisions.",
        "finance_meaning": "Keep financial plans private; listen to intuition before investing.",
        "personal_growth_meaning": "Deepening spiritual practices and trusting inner guidance.",
        "symbolism": "Seated between black and white pillars wearing a pomegranate robe."
    },
    {
        "name": "The Empress",
        "arcana": "Major",
        "suit": None,
        "keywords": ["Femininity", "Abundance", "Nurturing", "Nature"],
        "meaning_upright": "Creativity, fertility, growth, abundance, and comfort.",
        "meaning_reversed": "Creative block, dependence, neglect, or feeling smothered.",
        "personality_meaning": "A warm, nurturing individual with strong creative instincts.",
        "relationship_meaning": "Harmonious love life, deepening bonds, and emotional warmth.",
        "career_meaning": "Period of high productivity and creative growth at work.",
        "finance_meaning": "Financial abundance and stability achieved through steady care.",
        "personal_growth_meaning": "Connecting with nature, body wellness, and self-care.",
        "symbolism": "A crowned queen seated among lush fields and flowing water."
    },
    {
        "name": "Ace of Cups",
        "arcana": "Minor",
        "suit": "Cups",
        "keywords": ["Love", "New Feelings", "Compassion", "Creativity"],
        "meaning_upright": "Overflowing emotion, spiritual awakening, new relationships, and grace.",
        "meaning_reversed": "Blocked emotions, emotional drain, self-love deficits, or sadness.",
        "personality_meaning": "An open-hearted person sensitive to emotional nuances.",
        "relationship_meaning": "Beginning of a powerful connection or renewed romantic spark.",
        "career_meaning": "Finding true passion and emotional fulfillment in projects.",
        "finance_meaning": "Emotional clarity around money; generosity and harmony.",
        "personal_growth_meaning": "Allowing love and compassion to heal past hurts.",
        "symbolism": "A chalice overflowing with five streams of water into a lily pond."
    }
]


def seed_tarot_cards():
    """Generates all SQL tables and seeds Tarot data into SQLite/PostgreSQL."""
    # Ensure all models attached to Base are generated prior to running queries
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        added_count = 0
        for card_data in TAROT_CARDS_DATA:
            existing_card = (
                db.query(TarotCard)
                .filter(TarotCard.name == card_data["name"])
                .first()
            )
            if not existing_card:
                card = TarotCard(**card_data)
                db.add(card)
                added_count += 1

        db.commit()
        print(f"Tarot database seeding complete. Added {added_count} new card(s).")
    except Exception as e:
        db.rollback()
        print(f"Error seeding tarot cards: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_tarot_cards()