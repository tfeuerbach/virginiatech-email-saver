import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from kms.kms_manager import KMSManager
from web.database import db
from web.models import (
    DEFAULT_CADENCE_DAYS,
    MAX_CADENCE_DAYS,
    MIN_CADENCE_DAYS,
    EncryptedCredential,
    SchedulerState,
)
from web.services import sms_notifier
from web.services.email_notifier import is_configured as smtp_configured
from web.services.login_scheduler import next_login_time

TIMEZONE_CHOICES = [
    ("America/New_York", "Eastern"),
    ("America/Chicago", "Central"),
    ("America/Denver", "Mountain"),
    ("America/Los_Angeles", "Pacific"),
    ("America/Anchorage", "Alaska"),
    ("Pacific/Honolulu", "Hawaii"),
    ("UTC", "UTC"),
]
TIMEZONE_LABELS = {k: v for k, v in TIMEZONE_CHOICES}


def tz_display(iana_name):
    return TIMEZONE_LABELS.get(iana_name, iana_name)


dashboard_bp = Blueprint("dashboard", __name__)

kms_manager = KMSManager()


def get_authenticated_email():
    return session.get("authenticated_email")


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    email = get_authenticated_email()
    if not email:
        return redirect(url_for("form.index"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        session.clear()
        return redirect(url_for("form.index"))

    if credential.encrypted_key == "TEST_ACCOUNT_NO_REAL_CREDENTIALS":
        username = "testuser"
    else:
        decrypted_credentials = kms_manager.decrypt(credential.encrypted_key)
        _, username, _ = decrypted_credentials.split("|", maxsplit=2)

    cadence = credential.login_cadence_days or DEFAULT_CADENCE_DAYS
    next_login = next_login_time(credential)
    sched = SchedulerState.get()

    return render_template(
        "dashboard.html",
        vt_email=credential.vt_email,
        username=username,
        last_login=credential.last_login.strftime("%B %d, %Y, %I:%M %p") if credential.last_login else None,
        next_login=next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
        login_cadence_days=cadence,
        min_cadence=MIN_CADENCE_DAYS,
        max_cadence=MAX_CADENCE_DAYS,
        scheduler_running=sched.running,
        scheduler_next_check=sched.next_check.isoformat() if sched.next_check else None,
        scheduler_last_check=sched.last_check.isoformat() if sched.last_check else None,
        scheduler_last_result=sched.last_result,
        email_notifications_enabled=smtp_configured(),
        email_opt_in=credential.email_opt_in,
        notification_email=credential.effective_notification_email,
        has_custom_notification_email=credential.notification_email is not None,
        sms_opt_in=credential.sms_opt_in,
        phone_number=credential.phone_number or "",
        preferred_hour=credential.preferred_hour,
        timezone=credential.timezone,
        timezone_label=tz_display(credential.timezone) if credential.timezone else None,
        timezone_choices=TIMEZONE_CHOICES,
    )


@dashboard_bp.route("/update_cadence", methods=["POST"])
def update_cadence():
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
        return jsonify({"error": f"Cadence must be between {MIN_CADENCE_DAYS} and {MAX_CADENCE_DAYS} days"}), 400

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    credential.login_cadence_days = cadence
    db.session.commit()

    next_login = next_login_time(credential)
    next_login_str = next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None

    return jsonify(
        {
            "message": f"Login cadence updated to every {cadence} days",
            "login_cadence_days": cadence,
            "next_login": next_login_str,
        }
    )


@dashboard_bp.route("/update_timezone", methods=["POST"])
def update_timezone():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    tz_name = (data.get("timezone") or "").strip()

    if not tz_name:
        return jsonify({"error": "Timezone is required"}), 400

    try:
        ZoneInfo(tz_name)
    except (KeyError, Exception):
        return jsonify({"error": "Invalid timezone"}), 400

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    credential.timezone = tz_name
    db.session.commit()

    next_login = next_login_time(credential)
    return jsonify(
        {
            "message": f"Timezone set to {tz_display(tz_name)}",
            "timezone": tz_name,
            "timezone_label": tz_display(tz_name),
            "next_login": next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
        }
    )


@dashboard_bp.route("/update_preferred_time", methods=["POST"])
def update_preferred_time():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    raw_hour = data.get("preferred_hour")

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    if raw_hour is None or raw_hour == "":
        credential.preferred_hour = None
        db.session.commit()
        next_login = next_login_time(credential)
        return jsonify(
            {
                "message": "Preferred time cleared — logins will use UTC timing",
                "preferred_hour": None,
                "next_login": next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
            }
        )

    try:
        hour = int(raw_hour)
    except (ValueError, TypeError):
        return jsonify({"error": "Hour must be a number 0-23"}), 400

    if not (0 <= hour <= 23):
        return jsonify({"error": "Hour must be between 0 and 23"}), 400

    if not credential.timezone:
        return jsonify({"error": "Set your timezone first"}), 400

    credential.preferred_hour = hour
    db.session.commit()

    next_login = next_login_time(credential)
    tz_label = tz_display(credential.timezone)
    hour_12 = datetime(2000, 1, 1, hour).strftime("%I:%M %p")

    return jsonify(
        {
            "message": f"Logins scheduled at {hour_12} {tz_label}",
            "preferred_hour": hour,
            "next_login": next_login.strftime("%B %d, %Y, %I:%M %p") if next_login else None,
        }
    )


@dashboard_bp.route("/update_notification_email", methods=["POST"])
def update_notification_email():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    notif_email = (data.get("notification_email") or "").strip()

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    if not notif_email or notif_email == credential.vt_email:
        credential.notification_email = None
        db.session.commit()
        return jsonify(
            {
                "message": "Notifications will be sent to your VT email",
                "notification_email": credential.vt_email,
                "is_custom": False,
            }
        )

    if "@" not in notif_email or "." not in notif_email.split("@")[-1]:
        return jsonify({"error": "That doesn't look like a valid email"}), 400

    credential.notification_email = notif_email
    db.session.commit()

    return jsonify(
        {
            "message": f"Notifications will be sent to {notif_email}",
            "notification_email": notif_email,
            "is_custom": True,
        }
    )


@dashboard_bp.route("/update_email_opt_in", methods=["POST"])
def update_email_opt_in():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    opt_in = bool(data.get("email_opt_in"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    credential.email_opt_in = opt_in
    db.session.commit()

    return jsonify(
        {
            "message": "Email reminders " + ("enabled" if opt_in else "disabled"),
            "email_opt_in": opt_in,
        }
    )


@dashboard_bp.route("/download_calendar", methods=["GET"])
def download_calendar():
    email = get_authenticated_email()
    if not email:
        return redirect(url_for("form.index"))

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return redirect(url_for("form.index"))

    cadence = credential.login_cadence_days or DEFAULT_CADENCE_DAYS

    if credential.last_login:
        next_login = credential.last_login + timedelta(days=cadence)
        now = datetime.utcnow()
        while next_login < now:
            next_login += timedelta(days=cadence)
    else:
        next_login = datetime.utcnow() + timedelta(days=1)

    dtstart = next_login.strftime("%Y%m%dT%H%M%SZ")
    dtend = (next_login + timedelta(minutes=15)).strftime("%Y%m%dT%H%M%SZ")
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

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
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT1H\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:VT login in 1 hour — have your phone ready for Duo push\r\n"
        "END:VALARM\r\n"
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


E164_RE = re.compile(r"^\+1\d{10}$")


def normalise_phone(raw: str) -> str | None:
    """US/CA phone to E.164, or None if invalid."""
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return None
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"+1{digits}"


@dashboard_bp.route("/update_sms_preferences", methods=["POST"])
def update_sms_preferences():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    opt_in = bool(data.get("sms_opt_in"))
    raw_phone = (data.get("phone_number") or "").strip()

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "User not found"}), 404

    if opt_in:
        phone = normalise_phone(raw_phone)
        if phone is None:
            return jsonify({"error": "Please enter a valid 10-digit US phone number"}), 400
        credential.phone_number = phone
        credential.sms_opt_in = True
        db.session.commit()

        if sms_notifier.is_configured():
            sms_notifier.send_opt_in_confirmation(phone)

        return jsonify(
            {
                "message": "SMS notifications enabled",
                "phone_number": phone,
                "sms_opt_in": True,
            }
        )

    credential.sms_opt_in = False
    credential.phone_number = None
    db.session.commit()
    return jsonify(
        {
            "message": "SMS notifications disabled",
            "phone_number": "",
            "sms_opt_in": False,
        }
    )


@dashboard_bp.route("/delete_account", methods=["POST"])
def delete_account():
    email = get_authenticated_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    credential = EncryptedCredential.query.filter_by(vt_email=email).first()
    if not credential:
        return jsonify({"error": "Account not found"}), 404

    db.session.delete(credential)
    db.session.commit()
    session.clear()

    import logging

    logging.getLogger(__name__).info("Account deleted: %s", email)

    return jsonify({"message": "Account deleted", "redirect": "/"})
