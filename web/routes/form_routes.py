from flask import Blueprint, render_template, request, jsonify, current_app
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
    """Validate creds via Selenium, then encrypt and store them."""
    progress_updates = get_progress_store()
    print("Form submitted!")

    try:
        data = request.get_json()
        vt_email = data.get("vt_email")
        vt_username = data.get("vt_username")
        vt_password = data.get("vt_password")

        if not (vt_email and vt_username and vt_password):
            raise ValueError("All fields are required")
        if not vt_email.endswith("@vt.edu"):
            raise ValueError("Invalid Virginia Tech email address")

        print("Attempting to log in...")
        google_login = GoogleLogin()
        progress_updates["step"] = 2
        login_result = google_login.login(vt_email, vt_username, vt_password)

        if login_result["success"]:
            progress_updates["step"] = 4
            plaintext_credentials = f"{vt_email},{vt_username},{vt_password}"
            encrypted_credentials = kms_manager.encrypt(plaintext_credentials)

            existing_credential = EncryptedCredential.query.filter_by(vt_email=vt_email).first()
            if existing_credential:
                existing_credential.encrypted_key = encrypted_credentials
                existing_credential.last_login = datetime.utcnow()
                db.session.commit()
                message = "Credentials updated!"
            else:
                new_credential = EncryptedCredential(
                    vt_email=vt_email,
                    encrypted_key=encrypted_credentials,
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow(),
                )
                db.session.add(new_credential)
                db.session.commit()
                message = "Credentials saved!"

            return jsonify({"message": message, "redirect_url": f"/dashboard?email={vt_email}"})

        else:
            print(f"Login failed: {login_result['error']}")
            progress_updates["step"] = 5
            progress_updates["error"] = login_result["error"]
            return jsonify({"error": login_result["error"]}), 401

    except Exception as e:
        progress_updates["step"] = 5
        progress_updates["error"] = str(e)
        return jsonify({"error": str(e)}), 400
