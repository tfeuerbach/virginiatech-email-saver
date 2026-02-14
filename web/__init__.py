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

def _add_column_if_missing(app, table, column, col_type):
    """Add a column to an existing table if it doesn't exist yet.

    Only runs for Postgres — SQLite's create_all handles new DBs fine.
    """
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        return
    try:
        result = db.session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :tbl AND column_name = :col"
            ),
            {"tbl": table, "col": column},
        )
        if result.fetchone() is None:
            db.session.execute(
                text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}')
            )
            db.session.commit()
            logging.getLogger(__name__).info(
                "Migration: added %s.%s (%s)", table, column, col_type
            )
    except Exception as e:
        db.session.rollback()
        logging.getLogger(__name__).warning("Migration check failed: %s", e)


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

        # lightweight migration: add columns that db.create_all() won't add
        # to an existing table. safe to re-run — each one checks first.
        _add_column_if_missing(app, "encrypted_credential", "last_notification_sent", "TIMESTAMP")

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
