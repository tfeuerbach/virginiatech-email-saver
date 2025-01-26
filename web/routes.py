from datetime import datetime, timedelta
from flask import render_template, request, jsonify
from web.models import EncryptedCredential
from web.database import db
from kms.kms_manager import KMSManager

# Global variable to track progress
progress_updates = {"step": 0, "error": ""}

# Initialize KMS manager
kms_manager = KMSManager()


def register_routes(app):
    """Register all routes for the application"""

    @app.route("/", methods=["GET"])
    def index():
        global progress_updates
        progress_updates["step"] = 0  # Reset progress step to 0
        progress_updates["error"] = ""  # Clear any previous errors
        return render_template("form.html")

    @app.route("/submit", methods=["POST"])
    def submit():
        global progress_updates
        print("Form submitted!")

        try:
            data = request.get_json()
            vt_email = data.get("vt_email")
            vt_username = data.get("vt_username")
            vt_password = data.get("vt_password")
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            progress_updates["step"] = 5
            progress_updates["error"] = "Invalid JSON payload"
            return jsonify({"error": "Invalid JSON payload"}), 400

        if not (vt_email and vt_username and vt_password):
            progress_updates["step"] = 5
            progress_updates["error"] = "All fields are required"
            return jsonify({"error": "All fields are required"}), 400

        if not vt_email.endswith("@vt.edu"):
            progress_updates["step"] = 5
            progress_updates["error"] = "Invalid Virginia Tech email address"
            return jsonify({"error": "Invalid Virginia Tech email address"}), 400

        try:
            print("Attempting to log in...")
            from web.vt_google_login import login_to_google
            progress_updates["step"] = 2
            login_result = login_to_google(vt_email, vt_username, vt_password)

            if login_result["success"]:
                progress_updates["step"] = 4
                plaintext_credentials = f"{vt_email},{vt_username},{vt_password}"
                encrypted_credentials = kms_manager.encrypt(plaintext_credentials)

                existing_credential = EncryptedCredential.query.filter_by(vt_email=vt_email).first()

                if existing_credential:
                    existing_credential.encrypted_key = encrypted_credentials
                    existing_credential.last_login = datetime.utcnow()
                    existing_credential.created_at = datetime.utcnow()
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

                return jsonify({
                    "message": f"{message} Login attempt successful.",
                    "redirect_url": f"/dashboard?email={vt_email}"
                })

            else:
                print(f"Login failed: {login_result['error']}")
                progress_updates["step"] = 5
                progress_updates["error"] = login_result["error"]
                return jsonify({"error": login_result["error"]}), 401

        except Exception as e:
            print(f"Error during login: {e}")
            progress_updates["step"] = 5
            progress_updates["error"] = "An unexpected error occurred. Please try again later."
            return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

    @app.route("/dashboard", methods=["GET"])
    def dashboard():
        email = request.args.get("email")  # Get email from query params

        if not email:  # If no email is provided, redirect back to the form
            return render_template("form.html", error="No email provided. Please submit the form again.")

        credential = EncryptedCredential.query.filter_by(vt_email=email).first()

        if not credential:  # If user not found, redirect back to the form
            return render_template("form.html", error="User not found. Please try again.")

        decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
        username, _ = decrypted_credentials.split(",")[1:]  # Extract username only
        next_login = credential.last_login + timedelta(days=25) if credential.last_login else None

        return render_template(
            "dashboard.html",
            vt_email=credential.vt_email,
            username=username,
            last_login=credential.last_login.strftime("%B %d, %Y, %I:%M %p"),
            next_login=next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
        )

    @app.route("/update_progress", methods=["POST"])
    def update_progress():
        global progress_updates
        step = request.json.get("step", 0)
        if step > progress_updates["step"]:
            progress_updates["step"] = step
        print(f"Progress updated to step: {progress_updates['step']}")
        return jsonify({"status": "updated", "current_step": progress_updates["step"]})

    @app.route("/get_progress", methods=["GET"])
    def get_progress():
        print(f"Current progress: {progress_updates}")
        return jsonify(progress_updates)

    @app.route("/processing", methods=["GET"])
    def processing():
        return render_template("submit.html")
