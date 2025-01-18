import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential
from web.vt_google_login import login_to_google

# Define the instance path
instance_path = os.path.join(os.path.dirname(__file__), "instance")

# Ensure the instance directory exists
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Create the Flask app
app = Flask(__name__, instance_path=instance_path)

# Configure the database path inside the instance directory
db_path = os.path.join(instance_path, "encrypted_credentials.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initialize the database
with app.app_context():
    db.create_all()

# Global variable to track progress
progress_updates = {"step": 0}

kms_manager = KMSManager()

@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/submit", methods=["POST"])
def submit():
    print("Form submitted!")  # Debug print
    
    # Parse JSON data from the request
    try:
        data = request.get_json()
        vt_email = data.get("vt_email")
        vt_username = data.get("vt_username")
        vt_password = data.get("vt_password")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({"error": "Invalid JSON payload"}), 400

    if not (vt_email and vt_username and vt_password):
        return jsonify({"error": "All fields are required"}), 400

    # Combine credentials and encrypt
    plaintext_credentials = f"{vt_email},{vt_username},{vt_password}"
    encrypted_credentials = kms_manager.encrypt(plaintext_credentials)

    # Check if the email already exists in the database
    existing_credential = EncryptedCredential.query.filter_by(vt_email=vt_email).first()

    if existing_credential:
        existing_credential.encrypted_key = encrypted_credentials
        existing_credential.created_at = datetime.utcnow()
        db.session.commit()
        message = "Credentials updated successfully!"
    else:
        new_credential = EncryptedCredential(
            vt_email=vt_email,
            encrypted_key=encrypted_credentials,
            created_at=datetime.utcnow(),
        )
        db.session.add(new_credential)
        db.session.commit()
        message = "Credentials encrypted and saved successfully!"

    # Attempt to log in immediately
    try:
        print("Attempting to log in...")
        login_success = login_to_google(vt_email, vt_username, vt_password)
        if login_success:
            if existing_credential:
                existing_credential.last_login = datetime.utcnow()
                db.session.commit()
            else:
                new_credential.last_login = datetime.utcnow()
                db.session.commit()

            return jsonify({
                "message": f"{message} Login attempt successful.",
                "redirect_url": f"/dashboard?email={vt_email}"
            })
        else:
            message += " Login attempt failed. Please check your credentials."
    except Exception as e:
        print(f"Error during login: {e}")
        message += f" Login attempt failed with error: {e}"

    return jsonify({"message": message})

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

    # Render the dashboard with user data
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

    if step == 4 and progress_updates["step"] < 4:
        print("Login confirmed. Updating to step 4.")
    
    progress_updates["step"] = step
    return jsonify({"status": "updated", "current_step": step})

@app.route("/get_progress", methods=["GET"])
def get_progress():
    """Retrieve the current progress."""
    print(f"Current progress step: {progress_updates['step']}")  # Log current progress
    return jsonify(progress_updates)

@app.route("/confirm_login", methods=["POST"])
def confirm_login():
    email = request.json.get("email")
    credential = EncryptedCredential.query.filter_by(vt_email=email).first()

    if not credential or not credential.last_login:
        return jsonify({"success": False, "message": "Login not confirmed or user not found."})

    # Ensure step 4 is reached before confirming login
    if progress_updates["step"] == 4:
        return jsonify({"success": True, "message": "Login confirmed."})
    else:
        return jsonify({"success": False, "message": "Login in progress."})

# Start the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)