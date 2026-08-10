import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Palmistry & Tarot Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    
    # Security
    JWT_SECRET: str = Field(default="AETHERIA_MYSTIC_JWT_SECRET_KEY_FOR_LOCAL_DEV_0987654321", env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # PostgreSQL / SQLite
    DATABASE_URL: str = Field(default="sqlite:///./aetheria_sqlite.db", env="DATABASE_URL")
    
    # MongoDB
    MONGODB_URI: str = Field(default="mongodb://localhost:27017/aetheria", env="MONGODB_URI")
    MONGODB_DB_NAME: str = "aetheria"
    
    # OpenAI API
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
