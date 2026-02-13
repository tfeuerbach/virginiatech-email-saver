import os
import time
import logging
from flask import Flask
from sqlalchemy import text
from web.csrf import csrf
from web.database import db
from web.routes import register_routes
from web.services.login_scheduler import start_scheduler
from .config import ActiveConfig
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

def ensure_instance_dir(instance_path):
    """Create the instance dir if it doesn't exist yet."""
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

def wait_for_db(app):
    """Block until Postgres is accepting connections."""
    with app.app_context():
        retries = 5
        while retries > 0:
            try:
                db.session.execute(text("SELECT 1"))
                logging.getLogger(__name__).info("Database is ready!")
                return
            except Exception:
                logging.getLogger(__name__).info("Waiting for database... (%d/5)", 5 - retries)
                retries -= 1
                time.sleep(5)

def create_app():
    """Flask app factory."""
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(project_root, "instance")

    ensure_instance_dir(instance_path)

    app = Flask(__name__, instance_path=instance_path, static_folder="static")
    app.config.from_object(ActiveConfig)

    # Fix relative sqlite paths to be absolute
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_path, "encrypted_credentials.db")

    csrf.init_app(app)

    db.init_app(app)

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        wait_for_db(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    logger = logging.getLogger(__name__)
    logger.info("Running in %s mode (Debug=%s)", ActiveConfig.__name__, app.debug)

    # Start background login scheduler.
    # With flask dev server the reloader spawns a child — only start there.
    # With gunicorn (or anything else) there's no reloader, so always start.
    is_werkzeug_reloader_parent = (
        app.debug and os.environ.get("WERKZEUG_RUN_MAIN") is None
        and "gunicorn" not in (os.environ.get("SERVER_SOFTWARE") or "")
        and "gunicorn" not in __import__("sys").modules
    )
    if not is_werkzeug_reloader_parent:
        start_scheduler(app, interval_hours=24)

    return app
