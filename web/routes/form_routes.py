import logging
import threading
from datetime import datetime

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from kms.kms_manager import KMSManager
from web.database import db
from web.models import MAX_CADENCE_DAYS, MIN_CADENCE_DAYS, EncryptedCredential
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
        current_app.progress_updates = {"step": 0, "error": ""}
    return current_app.progress_updates


@form_bp.route("/", methods=["GET"])
def index():
    """Show the login form."""
    progress_updates = get_progress_store()
    progress_updates["step"] = 0
    progress_updates["error"] = ""
    return render_template("form.html")


@form_bp.route("/submit", methods=["POST"])
def submit():
    """Kick off the login flow in a background thread and return immediately.

    Sets the session cookie and step 1 right away so the client can
    navigate to /processing and start polling progress.
    """
    progress_updates = get_progress_store()

    data = request.get_json()
    vt_email = data.get("vt_email")
    vt_username = data.get("vt_username")
    vt_password = data.get("vt_password")

    if not (vt_email and vt_username and vt_password):
        return jsonify({"error": "All fields are required"}), 400
    if not vt_email.endswith("@vt.edu"):
        return jsonify({"error": "Invalid Virginia Tech email address"}), 400

    # --- dev/test shortcut: skip Selenium + KMS entirely ---
    if vt_email == TEST_EMAIL and vt_password == TEST_PASSWORD:
        logger.info("Test user login — bypassing Selenium and KMS")
        session["authenticated_email"] = vt_email

        existing = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
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

        # jump straight to "done" so the processing page redirects immediately
        progress_updates["step"] = 4
        progress_updates["error"] = ""
        return jsonify({"message": "Login started"})

    # Set the session now so the cookie travels with this response
    session["authenticated_email"] = vt_email

    # Mark step 1 immediately
    progress_updates["step"] = 1
    progress_updates["error"] = ""

    # Run the slow Selenium flow in a background thread
    app = current_app._get_current_object()

    def run_login():
        with app.app_context():
            try:
                google_login = GoogleLogin()
                progress_updates["step"] = 2
                login_result = google_login.login(vt_email, vt_username, vt_password)

                if login_result["success"]:
                    progress_updates["step"] = 4
                    plaintext = f"{vt_email},{vt_username},{vt_password}"
                    encrypted = kms_manager.encrypt(plaintext)

                    existing = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
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


@form_bp.route("/logout", methods=["GET"])
def logout():
    """Clear the session and send them back to the form."""
    session.clear()
    return redirect(url_for("form.index"))
