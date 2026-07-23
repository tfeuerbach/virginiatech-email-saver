from datetime import datetime
from unittest.mock import patch

from web.models import EncryptedCredential
from web.services.duo_notify import channels_after_change, has_duo_code_channel


def make_user(**overrides):
    defaults = dict(
        vt_email="test@vt.edu",
        encrypted_key="dummy",
        created_at=datetime.utcnow(),
        email_opt_in=True,
        sms_opt_in=False,
        phone_number=None,
    )
    defaults.update(overrides)
    return EncryptedCredential(**defaults)


@patch("web.services.duo_notify.email_notifier.is_configured", return_value=True)
@patch("web.services.duo_notify.sms_notifier.is_configured", return_value=True)
def test_has_duo_code_channel_with_email(mock_sms, mock_email, app):
    with app.app_context():
        user = make_user(email_opt_in=True, sms_opt_in=False)
        assert has_duo_code_channel(user) is True


@patch("web.services.duo_notify.email_notifier.is_configured", return_value=True)
@patch("web.services.duo_notify.sms_notifier.is_configured", return_value=True)
def test_has_duo_code_channel_requires_one_channel(mock_sms, mock_email, app):
    with app.app_context():
        user = make_user(email_opt_in=False, sms_opt_in=False)
        assert has_duo_code_channel(user) is False
        assert channels_after_change(user, sms_opt_in=True, phone_number="+15551234567") is True


@patch("web.services.duo_notify.email_notifier.is_configured", return_value=False)
@patch("web.services.duo_notify.sms_notifier.is_configured", return_value=False)
def test_has_duo_code_channel_when_services_unconfigured(mock_sms, mock_email, app):
    with app.app_context():
        user = make_user(email_opt_in=False, sms_opt_in=False)
        assert has_duo_code_channel(user) is True
