import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential

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

kms_manager = KMSManager()

@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/submit", methods=["POST"])
def submit():
    vt_email = request.form.get("vt_email")
    vt_username = request.form.get("vt_username")
    vt_password = request.form.get("vt_password")

    if not (vt_email and vt_username and vt_password):
        return jsonify({"error": "All fields are required"}), 400

    # Combine credentials and encrypt
    plaintext_credentials = f"{vt_email},{vt_username},{vt_password}"
    encrypted_credentials = kms_manager.encrypt(plaintext_credentials)

    # Save encrypted data to the database
    credential = EncryptedCredential(vt_email=vt_email, encrypted_key=encrypted_credentials)
    db.session.add(credential)
    db.session.commit()

    return jsonify({"message": "Credentials encrypted and saved successfully!"})

# Start the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
