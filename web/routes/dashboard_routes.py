from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
from web.database import db
from web.models import (
    EncryptedCredential,
    DEFAULT_CADENCE_DAYS,
    MIN_CADENCE_DAYS,
    MAX_CADENCE_DAYS,
)
from web.services.login_scheduler import scheduler_status
from kms.kms_manager import KMSManager

dashboard_bp = Blueprint("dashboard", __name__)

kms_manager = KMSManager()


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Show a user's dashboard (login history, cadence, scheduler info)."""
    email = request.args.get("email")
    if not email:
        return redirect(url_for("form.index"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return redirect(url_for("form.index"))

    decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
    username, _ = decrypted_credentials.split(",")[1:]

    cadence = credential.login_cadence_days or DEFAULT_CADENCE_DAYS
    next_login = (
        credential.last_login + timedelta(days=cadence)
        if credential.last_login
        else None
    )

    # Prevent refresh loops when already on the dashboard
    if request.referrer and "/dashboard" in request.referrer:
        return redirect(url_for("form.index"))

    return render_template(
        "dashboard.html",
        vt_email=credential.vt_email,
        username=username,
        last_login=credential.last_login.strftime("%B %d, %Y, %I:%M %p"),
        next_login=next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
        login_cadence_days=cadence,
        min_cadence=MIN_CADENCE_DAYS,
        max_cadence=MAX_CADENCE_DAYS,
        scheduler_running=scheduler_status["running"],
        scheduler_next_check=scheduler_status.get("next_check"),
        scheduler_last_check=scheduler_status.get("last_check"),
        scheduler_last_result=scheduler_status.get("last_check_result"),
    )


@dashboard_bp.route("/update_cadence", methods=["POST"])
def update_cadence():
    """Let the user change how often we auto-login for them."""
    data = request.get_json()
    email = data.get("email")
    cadence = data.get("login_cadence_days")

    if not email or cadence is None:
        return jsonify({"error": "email and login_cadence_days are required"}), 400

    try:
        cadence = int(cadence)
    except (ValueError, TypeError):
        return jsonify({"error": "login_cadence_days must be a number"}), 400

    if cadence < MIN_CADENCE_DAYS or cadence > MAX_CADENCE_DAYS:
        return jsonify({
            "error": f"Cadence must be between {MIN_CADENCE_DAYS} and {MAX_CADENCE_DAYS} days"
        }), 400

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    credential.login_cadence_days = cadence
    db.session.commit()

    next_login = None
    if credential.last_login:
        next_login = (credential.last_login + timedelta(days=cadence)).strftime(
            "%B %d, %Y, %I:%M %p"
        )

    return jsonify({
        "message": f"Login cadence updated to every {cadence} days",
        "login_cadence_days": cadence,
        "next_login": next_login,
    })
