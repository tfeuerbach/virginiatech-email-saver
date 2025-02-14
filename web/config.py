import os
import secrets
from dotenv import load_dotenv

# Load environment variables from `.env`
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(basedir, ".env"))

print("FLASK_ENV =", os.getenv("FLASK_ENV"))
print("DATABASE_URL =", os.getenv("DATABASE_URL"))


class Config:
    """Base configuration class. Loads values from environment variables."""
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1
    KMS_KEY_ID = os.getenv("KMS_KEY_ID")

    # Generate a strong random secret key if not set in .env
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Configuration for development environment using SQLite."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///../instance/encrypted_credentials.db"
    )

class ProductionConfig(Config):
    """Configuration for production environment using Dockerized PostgreSQL."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/mydatabase"
    )

# Mapping environment names to config classes
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}

# Default to DevelopmentConfig if FLASK_ENV is not set
FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
ActiveConfig = config_map.get(FLASK_ENV, DevelopmentConfig)  # Use development by default
