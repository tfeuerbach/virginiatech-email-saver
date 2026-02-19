import logging

from flask import current_app

logger = logging.getLogger(__name__)

# lazy-init so we don't import twilio at module level when it's not installed
_client = None


def _get_client():
    """Return a cached Twilio REST client, or None if not configured."""
    global _client
    sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    if _client is None:
        from twilio.rest import Client

        _client = Client(sid, token)
    return _client


def is_configured():
    """True when all three Twilio env vars are present."""
    cfg = current_app.config
    return bool(cfg.get("TWILIO_ACCOUNT_SID") and cfg.get("TWILIO_AUTH_TOKEN") and cfg.get("TWILIO_FROM_NUMBER"))


def _send(to_number: str, body: str) -> bool:
    """Send a single SMS. Returns True on success, False on failure (never raises)."""
    client = _get_client()
    if client is None:
        logger.debug("Twilio not configured, skipping SMS for %s", to_number)
        return False

    from_number = current_app.config["TWILIO_FROM_NUMBER"]

    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        logger.info("SMS sent to %s (sid=%s)", to_number, message.sid)
        return True
    except Exception as e:
        logger.error("Failed to send SMS to %s: %s", to_number, e)
        return False


def send_opt_in_confirmation(to_number: str) -> bool:
    """Send the welcome text when a user first opts in."""
    return _send(
        to_number,
        (
            "VT Email Saver: You're now subscribed to login reminders. "
            "You'll get a text ~1 min before each scheduled login so you "
            "can approve the Duo push.\n\n"
            "Reply STOP to unsubscribe."
        ),
    )


def send_login_sms(to_number: str) -> bool:
    """Fire off the pre-login heads-up text."""
    return _send(
        to_number,
        (
            "VT Email Saver: Your scheduled VT Gmail login is about to run. "
            "Keep your phone handy and approve the Duo push when it arrives.\n\n"
            "Reply STOP to unsubscribe."
        ),
    )
