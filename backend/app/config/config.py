from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Palmistry & Tarot Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security: production must provide a strong secret through the environment.
    JWT_SECRET: str = Field(default="", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=5, le=1440)

    # Persistence. Production deployments should use PostgreSQL.
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/aetheria"
    MONGODB_URI: str = "mongodb://mongodb:27017/aetheria"
    MONGODB_DB_NAME: str = "aetheria"

    # AI provider is optional; when absent, the platform uses its deterministic
    # symbolic interpretation engine based only on the user's actual reading.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Browser origins are supplied as a comma-separated environment value.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins(self):
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
