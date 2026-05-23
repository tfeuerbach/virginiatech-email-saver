import logging
import os
import time

from flask import Flask, render_template
from sqlalchemy import text

from web.csrf import csrf
from web.database import db
from web.routes import register_routes
from web.services.login_scheduler import start_scheduler

from .config import ActiveConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def ensure_instance_dir(instance_path):
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)


def wait_for_db(app, max_retries=15, wait_seconds=3):
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
                db.engine.dispose()
                logger.info("Waiting for database... (%d/%d)", attempt, max_retries)
                time.sleep(wait_seconds)

        raise RuntimeError(f"Could not connect to database after {max_retries} attempts")


def add_column_if_missing(app, table, column, col_type):
    """Bolt on a column if it doesn't exist. Postgres only."""
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        return
    try:
        result = db.session.execute(
            text("SELECT 1 FROM information_schema.columns WHERE table_name = :tbl AND column_name = :col"),
            {"tbl": table, "col": column},
        )
        if result.fetchone() is None:
            db.session.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}'))
            db.session.commit()
            logging.getLogger(__name__).info("Migration: added %s.%s (%s)", table, column, col_type)
    except Exception as e:
        db.session.rollback()
        logging.getLogger(__name__).warning("Migration check failed: %s", e)


def create_app():
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(project_root, "instance")

    ensure_instance_dir(instance_path)

    app = Flask(__name__, instance_path=instance_path, static_folder="static")
    app.config.from_object(ActiveConfig)

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_path, "encrypted_credentials.db")

    csrf.init_app(app)

    db.init_app(app)

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        wait_for_db(app)

    with app.app_context():
        db.create_all()

        add_column_if_missing(app, "encrypted_credential", "email_opt_in", "BOOLEAN DEFAULT TRUE")
        add_column_if_missing(app, "encrypted_credential", "notification_email", "VARCHAR(120)")
        add_column_if_missing(app, "encrypted_credential", "last_notification_sent", "TIMESTAMP")
        add_column_if_missing(app, "encrypted_credential", "phone_number", "VARCHAR(20)")
        add_column_if_missing(app, "encrypted_credential", "sms_opt_in", "BOOLEAN DEFAULT FALSE")
        add_column_if_missing(app, "encrypted_credential", "welcome_email_sent", "BOOLEAN DEFAULT FALSE")
        add_column_if_missing(app, "encrypted_credential", "preferred_hour", "INTEGER")
        add_column_if_missing(app, "encrypted_credential", "timezone", "VARCHAR(50)")

    register_routes(app)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval' https://cdn.jsdelivr.net https://esm.sh blob:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https://esm.sh https://cdn.jsdelivr.net; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none';"
        )
        return response

    logger = logging.getLogger(__name__)
    logger.info("Running in %s mode (Debug=%s)", ActiveConfig.__name__, app.debug)

    is_werkzeug_reloader_parent = (
        app.debug
        and os.environ.get("WERKZEUG_RUN_MAIN") is None
        and "gunicorn" not in (os.environ.get("SERVER_SOFTWARE") or "")
        and "gunicorn" not in __import__("sys").modules
    )
    if not app.config.get("TESTING") and not os.environ.get("TESTING") and not is_werkzeug_reloader_parent:
        start_scheduler(app)

    return app
