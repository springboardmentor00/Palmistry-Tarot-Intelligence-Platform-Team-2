import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config.config import settings
from backend.app.database.postgres import create_tables
from backend.app.database.seed_tarot import seed_tarot_cards
from backend.app.api.auth import router as auth_router
from backend.app.api.endpoints import router as ops_router
from backend.app.api.admin import router as admin_router
from backend.app.api.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup tasks: directory creation, table auto-generation, and tarot seeding."""
    os.makedirs("static/palm_images", exist_ok=True)
    create_tables()
    try:
        seed_tarot_cards()
    except Exception as e:
        print(f"Startup tarot seeding notice: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A professional, full-stack AI platform linking Palmistry & Tarot with CV algorithms.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(ops_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "platform": settings.PROJECT_NAME,
        "mode": "production" if getattr(settings, "OPENAI_API_KEY", None) else "demo",
    }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)