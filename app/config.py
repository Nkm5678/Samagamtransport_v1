import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Samagam Transport Platform"
    APP_VERSION: str = "4.0.0"
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./samagam_production.db")
    GEOFENCE_RADIUS_METERS: float = 2000.0
    SMTP_SERVER: str = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_SENDER_EMAIL: str = os.environ.get("SMTP_SENDER_EMAIL", "samagamtransport@gmail.com")
    SMTP_APP_PASSWORD: str = os.environ.get("SMTP_APP_PASSWORD", "")

settings = Settings()
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
