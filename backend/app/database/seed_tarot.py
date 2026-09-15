from backend.app.database.postgres import SessionLocal
from backend.app.models.sql_models import TarotCard
from backend.app.services.tarot_deck import TarotDeckService


def seed_tarot_cards():
    """Idempotently ensure the reference Tarot deck exists."""
    db = SessionLocal()
    try:
        TarotDeckService.seed_tarot_deck(db)
        return db.query(TarotCard).count()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(f"Tarot reference deck ready: {seed_tarot_cards()} cards")
