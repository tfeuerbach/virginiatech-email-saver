from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from web.models import EncryptedCredential
from kms.kms_manager import KMSManager

dashboard_bp = Blueprint("dashboard", __name__)

kms_manager = KMSManager()

@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Render the dashboard for a specific user."""
    email = request.args.get("email")
    if not email:
        return render_template("form.html", error="No email provided. Please submit the form again.")

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return render_template("form.html", error="User not found. Please try again.")

    decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
    username, _ = decrypted_credentials.split(",")[1:]
    next_login = credential.last_login + timedelta(days=25) if credential.last_login else None

    return render_template(
        "dashboard.html",
        vt_email=credential.vt_email,
        username=username,
        last_login=credential.last_login.strftime("%B %d, %Y, %I:%M %p"),
        next_login=next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
    )
