import os
import secrets
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(basedir, ".env"))

print("FLASK_ENV =", os.getenv("FLASK_ENV"))
print("DATABASE_URL =", os.getenv("DATABASE_URL"))


class Config:
    """Shared config — everything reads from .env."""
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    KMS_KEY_ID = os.getenv("KMS_KEY_ID")

    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Local dev — SQLite fallback."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///../instance/encrypted_credentials.db"
    )

class ProductionConfig(Config):
    """Docker / deployed — expects Postgres."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/mydatabase"
    )

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
ActiveConfig = config_map.get(FLASK_ENV, DevelopmentConfig)
