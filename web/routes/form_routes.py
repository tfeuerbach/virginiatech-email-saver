import logging
import threading
from datetime import datetime

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from kms.kms_manager import KMSManager
from web.database import db
from web.models import MAX_CADENCE_DAYS, MIN_CADENCE_DAYS, EncryptedCredential
from web.services.email_notifier import is_configured as smtp_configured
from web.services.email_notifier import send_welcome_email
from web.services.google_login import GoogleLogin

logger = logging.getLogger(__name__)

form_bp = Blueprint("form", __name__)
kms_manager = KMSManager()

# dev/test account — bypasses Selenium + KMS entirely
TEST_EMAIL = "test@vt.edu"
TEST_PASSWORD = "testuser"


def get_progress_store():
    """Get the shared progress dict (lives on the app object)."""
    if not hasattr(current_app, "progress_updates"):
        current_app.progress_updates = {"step": 0, "error": "", "duo_code": ""}
    return current_app.progress_updates


def reset_progress(progress_updates):
    progress_updates["step"] = 0
    progress_updates["error"] = ""
    progress_updates["duo_code"] = ""


@form_bp.route("/", methods=["GET"])
def index():
    """Show the login form."""
    progress_updates = get_progress_store()
    reset_progress(progress_updates)
    return render_template("form.html")


@form_bp.route("/submit", methods=["POST"])
def submit():
    """Kick off the login flow in a background thread."""
    progress_updates = get_progress_store()

    data = request.get_json()
    vt_email = data.get("vt_email")
    vt_username = data.get("vt_username")
    vt_password = data.get("vt_password")

    if not (vt_email and vt_username and vt_password):
        return jsonify({"error": "All fields are required"}), 400
    if not vt_email.endswith("@vt.edu"):
        return jsonify({"error": "Invalid Virginia Tech email address"}), 400

    if vt_email == TEST_EMAIL and vt_password == TEST_PASSWORD:
        logger.info("Test user login — bypassing Selenium and KMS")
        session["authenticated_email"] = vt_email

        existing = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
        is_new_account = existing is None
        if existing:
            existing.last_login = datetime.utcnow()
            db.session.commit()
        else:
            db.session.add(
                EncryptedCredential(
                    vt_email=vt_email,
                    encrypted_key="TEST_ACCOUNT_NO_REAL_CREDENTIALS",
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow(),
                )
            )
            db.session.commit()

        if is_new_account and smtp_configured():
            cred = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
            if send_welcome_email(vt_email, cred.login_cadence_days):
                cred.welcome_email_sent = True
                db.session.commit()

        progress_updates["step"] = 4
        progress_updates["error"] = ""
        return jsonify({"message": "Login started"})

    session["authenticated_email"] = vt_email
    reset_progress(progress_updates)
    progress_updates["step"] = 1

    app = current_app._get_current_object()

    def run_login():
        with app.app_context():
            try:
                google_login = GoogleLogin()
                progress_updates["step"] = 2
                login_result = google_login.login(vt_email, vt_username, vt_password)

                if login_result["success"]:
                    progress_updates["step"] = 4
                    plaintext = f"{vt_email}|{vt_username}|{vt_password}"
                    encrypted = kms_manager.encrypt(plaintext)

                    existing = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
                    is_new_account = existing is None
                    if existing:
                        existing.encrypted_key = encrypted
                        existing.last_login = datetime.utcnow()
                        db.session.commit()
                    else:
                        new_cred = EncryptedCredential(
                            vt_email=vt_email,
                            encrypted_key=encrypted,
                            created_at=datetime.utcnow(),
                            last_login=datetime.utcnow(),
                        )
                        db.session.add(new_cred)
                        db.session.commit()

                    if is_new_account and smtp_configured():
                        cred = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
                        if send_welcome_email(vt_email, cred.login_cadence_days):
                            cred.welcome_email_sent = True
                            db.session.commit()
                else:
                    progress_updates["step"] = 5
                    progress_updates["error"] = login_result["error"]

            except Exception as e:
                progress_updates["step"] = 5
                progress_updates["error"] = str(e)

    thread = threading.Thread(target=run_login, daemon=True)
    thread.start()

    return jsonify({"message": "Login started"})


@form_bp.route("/privacy", methods=["GET"])
def privacy():
    """Public privacy policy page (no auth required)."""
    return render_template(
        "privacy.html",
        min_cadence=MIN_CADENCE_DAYS,
        max_cadence=MAX_CADENCE_DAYS,
    )


@form_bp.route("/terms", methods=["GET"])
def terms():
    """Public terms of service page (no auth required)."""
    return render_template("terms.html")


@form_bp.route("/sms-consent", methods=["GET"])
def sms_consent():
    """Public SMS opt-in disclosure page for Twilio verification."""
    return render_template(
        "sms_consent.html",
        min_cadence=MIN_CADENCE_DAYS,
        max_cadence=MAX_CADENCE_DAYS,
    )


@form_bp.route("/logout", methods=["GET"])
def logout():
    """Clear the session and send them back to the form."""
    session.clear()
    return redirect(url_for("form.index"))
