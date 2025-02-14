from flask import Blueprint, render_template, request, redirect, url_for
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
        return redirect(url_for("form.index"))  # Redirect to home if no email

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return redirect(url_for("form.index"))  # Redirect if user not found

    decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
    username, _ = decrypted_credentials.split(",")[1:]
    next_login = credential.last_login + timedelta(days=25) if credential.last_login else None

    # Check if user is coming from the dashboard and redirect them to "/"
    if request.referrer and "/dashboard" in request.referrer:
        return redirect(url_for("form.index"))

    return render_template(
        "dashboard.html",
        vt_email=credential.vt_email,
        username=username,
        last_login=credential.last_login.strftime("%B %d, %Y, %I:%M %p"),
        next_login=next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
    )
