import os
import secrets
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Shared config — everything reads from .env."""
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    KMS_KEY_ID = os.getenv("KMS_KEY_ID")

    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # SMTP for email notifications (optional — leave blank to disable)
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = os.getenv("SMTP_PORT", "587")
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@vtemailsaver.tfeuerbach.dev")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VT Email Saver")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true")

class DevelopmentConfig(Config):
    """Local dev — SQLite fallback, cookies don't require HTTPS."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///../instance/encrypted_credentials.db"
    )
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Docker / deployed — expects Postgres, cookies require HTTPS."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/mydatabase"
    )
    SESSION_COOKIE_SECURE = True

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
ActiveConfig = config_map.get(FLASK_ENV, DevelopmentConfig)
