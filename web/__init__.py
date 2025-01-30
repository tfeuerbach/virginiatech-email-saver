import os
from flask import Flask
from web.database import db
from web.routes import register_routes
from .config import ActiveConfig

def ensure_instance_dir(instance_path):
    """Ensure the instance directory exists."""
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        print(f"Created instance directory at: {instance_path}")

def create_app():
    """App factory function."""
    # Define instance path at the root level of the project
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))  # Go up one level
    instance_path = os.path.join(project_root, "instance")

    # Ensure the instance directory exists
    ensure_instance_dir(instance_path)

    # Create Flask app with instance path
    app = Flask(__name__, instance_path=instance_path)

    # Load configuration dynamically based on FLASK_ENV
    app.config.from_object(ActiveConfig)

    # Initialize the database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Register routes
    register_routes(app)

    print(f"🛠️ Running in {ActiveConfig.__name__} mode")  # Debug log
    return app