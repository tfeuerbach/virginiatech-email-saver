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
    """mkdir -p for the instance folder."""
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

def wait_for_db(app, max_retries=15, wait_seconds=3):
    """Block until Postgres is accepting connections.

    After every failed attempt we dispose the entire connection pool so
    SQLAlchemy doesn't hand a stale/dead connection to db.create_all().
    """
    logger = logging.getLogger(__name__)
    with app.app_context():
        for attempt in range(1, max_retries + 1):
            try:
                db.session.execute(text("SELECT 1"))
                db.session.commit()
                logger.info("Database is ready (attempt %d/%d)", attempt, max_retries)
                return
            except Exception:
                db.session.rollback()
                db.engine.dispose()          # kill any pooled dead connections
                logger.info(
                    "Waiting for database... (%d/%d)", attempt, max_retries
                )
                time.sleep(wait_seconds)

        raise RuntimeError(
            f"Could not connect to database after {max_retries} attempts"
        )

def _add_column_if_missing(app, table, column, col_type):
    """Poor-man's migration — skips if column already exists. Postgres only."""
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

    # make sqlite paths absolute so they land in instance/
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_path, "encrypted_credentials.db")

    csrf.init_app(app)

    db.init_app(app)

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        wait_for_db(app)

    with app.app_context():
        db.create_all()

        # db.create_all() won't touch existing tables — bolt on new columns here
        _add_column_if_missing(app, "encrypted_credential", "email_opt_in", "BOOLEAN DEFAULT TRUE")
        _add_column_if_missing(app, "encrypted_credential", "notification_email", "VARCHAR(120)")
        _add_column_if_missing(app, "encrypted_credential", "last_notification_sent", "TIMESTAMP")
        _add_column_if_missing(app, "encrypted_credential", "phone_number", "VARCHAR(20)")
        _add_column_if_missing(app, "encrypted_credential", "sms_opt_in", "BOOLEAN DEFAULT FALSE")

    register_routes(app)

    logger = logging.getLogger(__name__)
    logger.info("Running in %s mode (Debug=%s)", ActiveConfig.__name__, app.debug)

    # avoid double-starting the scheduler in Flask's reloader parent process
    is_werkzeug_reloader_parent = (
        app.debug and os.environ.get("WERKZEUG_RUN_MAIN") is None
        and "gunicorn" not in (os.environ.get("SERVER_SOFTWARE") or "")
        and "gunicorn" not in __import__("sys").modules
    )
    if not is_werkzeug_reloader_parent:
        start_scheduler(app, interval_hours=24)

    return app
