import os
import secrets

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CORS_ORIGINS"] = "http://testserver"

from sqlalchemy.pool import StaticPool
from backend.app.config.config import settings
from backend.app.database import postgres

postgres.engine.dispose()
postgres.engine = postgres.create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
postgres.SessionLocal.configure(bind=postgres.engine)
from backend.app.database.seed_tarot import seed_tarot_cards
from backend.app.models.sql_models import Base

Base.metadata.create_all(bind=postgres.engine)
seed_tarot_cards()

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
