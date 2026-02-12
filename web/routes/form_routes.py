import threading
from flask import Blueprint, render_template, request, jsonify, current_app, session
from datetime import datetime
from web.models import EncryptedCredential
from web.database import db
from kms.kms_manager import KMSManager
from web.services.google_login import GoogleLogin

form_bp = Blueprint("form", __name__)
kms_manager = KMSManager()

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

@form_bp.route("/logout", methods=["GET"])
def logout():
    """Clear the session and send them back to the form."""
    session.clear()
    return render_template("form.html")
