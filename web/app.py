import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from web.database import db
from web.routes import register_routes


def create_app():
    """App factory function"""
    # Define the instance path
    instance_path = os.path.join(os.path.dirname(__file__), "instance")

    # Ensure the instance directory exists
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    # Create the Flask app
    app = Flask(__name__, instance_path=instance_path)

    # Configure the database path inside the instance directory
    db_path = os.path.join(instance_path, "encrypted_credentials.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize the database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Register routes
    register_routes(app)

    return app
