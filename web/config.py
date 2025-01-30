import os
from dotenv import load_dotenv

# Load environment variables from `.env`
load_dotenv()

class Config:
    """Base configuration class. Loads values from environment variables."""
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1
    KMS_KEY_ID = os.getenv("KMS_KEY_ID")

    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")  # Add a default
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