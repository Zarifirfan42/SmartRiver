"""Configuration from environment."""

import os
from pathlib import Path


class Settings:
    """Application settings (env vars)."""

    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/smartriver",
    )

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    UPLOAD_DIR: Path = PROJECT_ROOT / "datasets" / "uploads"
    ML_MODELS_DIR: Path = PROJECT_ROOT / "ml_models"


settings = Settings()
