from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
from web.models import EncryptedCredential
from web.database import db
from kms.kms_manager import KMSManager
from web.services.google_login import GoogleLogin

form_bp = Blueprint("form", __name__)
kms_manager = KMSManager()

def get_progress_store():
    """Ensure progress tracking is shared across routes."""
    if not hasattr(current_app, "progress_updates"):
        current_app.progress_updates = {"step": 0, "error": ""}
    return current_app.progress_updates

@form_bp.route("/", methods=["GET"])
def index():
    """Render the form page."""
    progress_updates = get_progress_store()
    progress_updates["step"] = 0  # Reset progress
    progress_updates["error"] = ""  # Clear errors
    return render_template("form.html")

@form_bp.route("/submit", methods=["POST"])
def submit():
    """Handle form submission and login process."""
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
                message = "Credentials updated successfully!"
            else:
                new_credential = EncryptedCredential(
                    vt_email=vt_email,
                    encrypted_key=encrypted_credentials,
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow(),
                )
                db.session.add(new_credential)
                db.session.commit()
                message = "Credentials encrypted and saved successfully!"

            return jsonify({"message": message, "redirect_url": f"/dashboard?email={vt_email}"})

        else:
            print(f"Login failed: {login_result['error']}")
            progress_updates["step"] = 5
            progress_updates["error"] = login_result["error"]
            print(f"Updated progress error: {progress_updates['error']}")  # Debugging output
            return jsonify({"error": login_result["error"]}), 401


    except Exception as e:
        progress_updates["step"] = 5
        progress_updates["error"] = str(e)
        return jsonify({"error": str(e)}), 400
