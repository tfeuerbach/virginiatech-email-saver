import logging

from flask import current_app

logger = logging.getLogger(__name__)

# lazy-init so we don't import twilio at module level when it's not installed
_client = None


def get_client():
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


def send(to_number: str, body: str) -> bool:
    """Send a single SMS. Returns True on success, False on failure (never raises)."""
    client = get_client()
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
    return send(
        to_number,
        (
            "VT Email Saver: You're now subscribed to login reminders. "
            "You'll get a text before each scheduled login with your Duo verification code.\n\n"
            "Reply STOP to unsubscribe."
        ),
    )


def send_login_sms(to_number: str) -> bool:
    """Fire off the pre-login heads-up text."""
    return send(
        to_number,
        (
            "VT Email Saver: Your scheduled VT Gmail login is about to run. "
            "You'll receive your Duo verification code shortly — open Duo Mobile "
            "and enter it when it arrives.\n\n"
            "Reply STOP to unsubscribe."
        ),
    )


def send_duo_code(to_number: str, code: str) -> bool:
    """Send the Duo passcode the user must enter in Duo Mobile."""
    return send(
        to_number,
        (
            f"VT Email Saver: Your Duo verification code is {code}. "
            "Open Duo Mobile and enter this code to approve your login.\n\n"
            "Reply STOP to unsubscribe."
        ),
    )
