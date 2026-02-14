import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)


def _get_smtp_config():
    """Pull SMTP settings from app config. Returns None if not configured."""
    host = current_app.config.get("SMTP_HOST")
    if not host:
        return None

    return {
        "host": host,
        "port": int(current_app.config.get("SMTP_PORT", 587)),
        "user": current_app.config.get("SMTP_USER", ""),
        "password": current_app.config.get("SMTP_PASSWORD", ""),
        "from_email": current_app.config.get(
            "SMTP_FROM_EMAIL", "noreply@vtemailsaver.tfeuerbach.dev"
        ),
        "from_name": current_app.config.get("SMTP_FROM_NAME", "VT Email Saver"),
        "use_tls": current_app.config.get("SMTP_USE_TLS", "true").lower()
        in ("true", "1", "yes"),
    }


def is_configured():
    """Quick check so callers can skip email logic entirely."""
    return bool(current_app.config.get("SMTP_HOST"))


def send_login_reminder(to_email, next_login_utc: datetime, cadence_days: int):
    """
    Send a friendly "your login is tomorrow" email.
    Returns True on success, False on failure (never raises).
    """
    config = _get_smtp_config()
    if config is None:
        logger.debug("SMTP not configured, skipping reminder for %s", to_email)
        return False

    next_str = next_login_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")

    subject = "VT Email Saver — Login Tomorrow, Have Your Phone Ready"

    html = f"""\
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
    .card {{ max-width: 500px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #630031, #1a0010); padding: 24px; text-align: center; color: #fff; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
    .body {{ padding: 24px; color: #333; line-height: 1.6; }}
    .highlight {{ background: #fff3e6; border-left: 4px solid #e87722; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; }}
    .highlight strong {{ color: #e87722; }}
    .cta {{ text-align: center; margin: 20px 0 8px; }}
    .footer {{ padding: 16px 24px; font-size: 12px; color: #999; text-align: center; border-top: 1px solid #eee; }}
</style>
</head>
<body>
<div class="card">
    <div class="header">
        <h1>VT Email Saver</h1>
    </div>
    <div class="body">
        <p>Hey there,</p>
        <p>Your scheduled VT Gmail login is coming up <strong>tomorrow</strong>.
           When it runs, Virginia Tech will send a <strong>Duo 2FA push notification</strong>
           to your phone — you'll need to approve it for the login to succeed.</p>

        <div class="highlight">
            <strong>Scheduled login:</strong> {next_str}<br>
            <strong>Cadence:</strong> every {cadence_days} days
        </div>

        <p>Just keep your phone handy around that time and tap <em>Approve</em> when the Duo push arrives.</p>

        <div class="cta">
            <p style="font-size: 13px; color: #888;">
                If you've added the calendar event, you'll get a reminder there too.
            </p>
        </div>
    </div>
    <div class="footer">
        VT Email Saver &middot; Automated by
        <a href="https://github.com/tfeuerbach/virginiatech-email-saver" style="color: #e87722; text-decoration: none;">tfeuerbach</a>
    </div>
</div>
</body>
</html>
"""

    plain = (
        f"Your VT Email Saver login is scheduled for tomorrow.\n\n"
        f"Scheduled login: {next_str}\n"
        f"Cadence: every {cadence_days} days\n\n"
        f"Keep your phone nearby to approve the Duo 2FA push notification.\n"
    )

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
        logger.info("Login reminder sent to %s", to_email)
        return True

    except Exception as e:
        logger.error("Failed to send reminder to %s: %s", to_email, e)
        return False
