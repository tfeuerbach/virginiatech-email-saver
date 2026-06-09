import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from flask import current_app, render_template

logger = logging.getLogger(__name__)


def get_smtp_config():
    """Pull SMTP settings from app config. Returns None if not configured."""
    host = current_app.config.get("SMTP_HOST")
    if not host:
        return None

    return {
        "host": host,
        "port": int(current_app.config.get("SMTP_PORT", 587)),
        "user": current_app.config.get("SMTP_USER", ""),
        "password": current_app.config.get("SMTP_PASSWORD", ""),
        "from_email": current_app.config.get("SMTP_FROM_EMAIL", "noreply@vtemailsaver.tfeuerbach.dev"),
        "from_name": current_app.config.get("SMTP_FROM_NAME", "VT Email Saver"),
        "use_tls": current_app.config.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
    }


def is_configured():
    """Quick check so callers can skip email logic entirely."""
    return bool(current_app.config.get("SMTP_HOST"))


def send_email(to_email, subject, html, plain):
    """Low-level SMTP send. Returns True on success, False on failure (never raises)."""
    config = get_smtp_config()
    if config is None:
        logger.debug("SMTP not configured, skipping email to %s", to_email)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config['from_name']} <{config['from_email']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if config["use_tls"]:
            server = smtplib.SMTP(config["host"], config["port"], timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=15)
            server.ehlo()

        if config["user"]:
            server.login(config["user"], config["password"])

        server.sendmail(config["from_email"], [to_email], msg.as_string())
        server.quit()
        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_welcome_email(to_email, cadence_days: int):
    """
    Send a one-time welcome email after first account creation.
    Returns True on success, False on failure (never raises).
    """
    base = current_app.config.get("BASE_URL", "https://vtemailsaver.tfeuerbach.dev").rstrip("/")
    dashboard_url = f"{base}/dashboard?user={quote(to_email)}"

    template_vars = {
        "vt_email": to_email,
        "cadence_days": cadence_days,
        "dashboard_url": dashboard_url,
    }
    html = render_template("emails/welcome.html", **template_vars)
    plain = render_template("emails/welcome.txt", **template_vars)

    subject = "Welcome to VT Email Saver — You're All Set"

    ok = send_email(to_email, subject, html, plain)
    if ok:
        logger.info("Welcome email sent to %s", to_email)
    return ok


def send_login_reminder(to_email, next_login_utc: datetime, cadence_days: int):
    """
    Send a friendly "your login is tomorrow" email.
    Returns True on success, False on failure (never raises).
    """
    next_str = next_login_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")

    subject = "VT Email Saver — Login Tomorrow, Have Your Phone Ready"

    template_vars = {"next_login": next_str, "cadence_days": cadence_days}
    html = render_template("emails/login_reminder.html", **template_vars)
    plain = render_template("emails/login_reminder.txt", **template_vars)

    ok = send_email(to_email, subject, html, plain)
    if ok:
        logger.info("Login reminder sent to %s", to_email)
    return ok
