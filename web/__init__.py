import os
import time
from flask import Flask
from web.database import db
from web.routes import register_routes
from .config import ActiveConfig

def ensure_instance_dir(instance_path):
    """Ensure the instance directory exists."""
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        print(f"Created instance directory at: {instance_path}")

def wait_for_db(app):
    """Wait until the database is available before proceeding."""
    with app.app_context():
        retries = 5
        while retries > 0:
            try:
                db.session.execute("SELECT 1")  # Simple DB connection test
                print("✅ Database is ready!")
                return
            except Exception as e:
                print(f"Waiting for database... ({5 - retries}/5)")
                retries -= 1
                time.sleep(5)

def create_app():
    """App factory function."""
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(project_root, "instance")

    # Ensure the instance directory exists
    ensure_instance_dir(instance_path)

    # Create Flask app
    app = Flask(__name__, instance_path=instance_path, static_folder="static")

    # Load configuration dynamically
    app.config.from_object(ActiveConfig)

    # Initialize the database
    db.init_app(app)

    # Wait for database if in production (Docker)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        wait_for_db(app)

    with app.app_context():
        db.create_all()

    # Register routes
    register_routes(app)

    print(f"🛠️ Running in {ActiveConfig.__name__} mode (Debug={app.debug})")
    print(f"🔐 Flask Secret Key Loaded: {ActiveConfig.SECRET_KEY[:8]}********")  # Debugging
    
    return app
