"""Helpers for delivering Duo verification codes to users."""

from web.services import email_notifier, sms_notifier


def has_duo_code_channel(credential) -> bool:
    """True when the user can receive a Duo code via email and/or SMS."""
    return channels_after_change(credential)


def channels_after_change(
    credential,
    *,
    email_opt_in=None,
    sms_opt_in=None,
    phone_number=None,
) -> bool:
    """True when the user would still have a Duo code channel after a settings change."""
    email_on = credential.email_opt_in if email_opt_in is None else email_opt_in
    sms_on = credential.sms_opt_in if sms_opt_in is None else sms_opt_in
    phone = credential.phone_number if phone_number is None else phone_number

    email_ok = email_notifier.is_configured() and email_on
    sms_ok = sms_notifier.is_configured() and sms_on and bool(phone)
    if not email_notifier.is_configured() and not sms_notifier.is_configured():
        return True
    return email_ok or sms_ok


def deliver_duo_code(credential, code: str) -> bool:
    """Send the Duo code through every channel the user has enabled."""
    sent = False

    if credential.sms_opt_in and credential.phone_number and sms_notifier.is_configured():
        if sms_notifier.send_duo_code(credential.phone_number, code):
            sent = True

    if credential.email_opt_in and email_notifier.is_configured():
        if email_notifier.send_duo_code(credential.effective_notification_email, code):
            sent = True

    return sent
