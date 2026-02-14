from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, session, Response,
)
from datetime import datetime, timedelta
from web.database import db
from web.models import (
    EncryptedCredential,
    DEFAULT_CADENCE_DAYS,
    MIN_CADENCE_DAYS,
    MAX_CADENCE_DAYS,
)
from web.services.login_scheduler import scheduler_status
from web.services.email_notifier import is_configured as smtp_configured
from kms.kms_manager import KMSManager

dashboard_bp = Blueprint("dashboard", __name__)

kms_manager = KMSManager()


def get_authenticated_email():
    """Return the session email, or None if not logged in."""
    return session.get("authenticated_email")


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Show the authenticated user's dashboard."""
    email = get_authenticated_email()
    if not email:
        return redirect(url_for("form.index"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        session.clear()
        return redirect(url_for("form.index"))

    # test account stores a placeholder, skip KMS decryption
    if credential.encrypted_key == "TEST_ACCOUNT_NO_REAL_CREDENTIALS":
        username = "testuser"
    else:
        decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
        username, _ = decrypted_credentials.split(",")[1:]

    cadence = credential.login_cadence_days or DEFAULT_CADENCE_DAYS
    next_login = (
        credential.last_login + timedelta(days=cadence)
        if credential.last_login
        else None
    )

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
        email_notifications_enabled=smtp_configured(),
    )


@dashboard_bp.route("/update_cadence", methods=["POST"])
def update_cadence():
    """Let the user change how often we auto-login for them."""
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    cadence = data.get("login_cadence_days")

    if cadence is None:
        return jsonify({"error": "login_cadence_days is required"}), 400

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


@dashboard_bp.route("/download_calendar", methods=["GET"])
def download_calendar():
    """Generate a recurring .ics file for the user's login schedule.

    Works with Apple Calendar, Google Calendar, Outlook — anything
    that speaks iCalendar (RFC 5545).
    """
    email = get_authenticated_email()
    if not email:
        return redirect(url_for("form.index"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return redirect(url_for("form.index"))

    cadence = credential.login_cadence_days or DEFAULT_CADENCE_DAYS

    # figure out the first event date (next scheduled login)
    if credential.last_login:
        next_login = credential.last_login + timedelta(days=cadence)
        # if next_login is in the past, fast-forward to the next one
        now = datetime.utcnow()
        while next_login < now:
            next_login += timedelta(days=cadence)
    else:
        # no login yet — start from tomorrow
        next_login = datetime.utcnow() + timedelta(days=1)

    dtstart = next_login.strftime("%Y%m%dT%H%M%SZ")
    dtend = (next_login + timedelta(minutes=15)).strftime("%Y%m%dT%H%M%SZ")
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # UID should be stable per-user so re-downloading replaces the old event
    uid = f"vtemailsaver-{email.replace('@', '-at-')}"

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//VT Email Saver//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "X-WR-CALNAME:VT Email Saver\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"RRULE:FREQ=DAILY;INTERVAL={cadence}\r\n"
        "SUMMARY:VT Email Saver — Approve Duo Push\r\n"
        "DESCRIPTION:Your automated VT Gmail login is happening now. "
        "Keep your phone nearby and approve the Duo 2FA push notification "
        "when it arrives.\r\n"
        # 1 hour before
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT1H\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:VT login in 1 hour — have your phone ready for Duo push\r\n"
        "END:VALARM\r\n"
        # 15 minutes before
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT15M\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:VT login in 15 minutes — have your phone ready for Duo push\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    return Response(
        ics,
        mimetype="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=vt-email-saver.ics",
        },
    )
