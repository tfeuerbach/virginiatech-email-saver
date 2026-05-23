from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from web.database import db
from web.models import EncryptedCredential
from web.services.login_scheduler import next_login_time, send_login_reminders


def make_user(**overrides):
    defaults = {
        "last_login": datetime(2026, 1, 1, 12, 0, 0),
        "login_cadence_days": 25,
        "preferred_hour": None,
        "timezone": None,
    }
    defaults.update(overrides)
    user = MagicMock(**defaults)
    return user



def test_no_last_login_returns_none():
    user = make_user(last_login=None)
    assert next_login_time(user) is None


def test_plain_cadence_anchor():
    user = make_user(last_login=datetime(2026, 1, 1, 12, 0, 0), login_cadence_days=10)
    result = next_login_time(user)
    assert result == datetime(2026, 1, 11, 12, 0, 0)


def test_preferred_hour_pins_to_local_time():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=10,
        preferred_hour=9,
        timezone="America/New_York",
    )
    with patch("web.services.login_scheduler.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 2, 0, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = next_login_time(user)

    assert result is not None
    assert result.hour == 14  # 9 AM ET = 14:00 UTC
    assert result.minute == 0


def test_preferred_hour_bumps_forward_if_before_anchor():
    user = make_user(
        last_login=datetime(2026, 1, 1, 20, 0, 0),
        login_cadence_days=1,
        preferred_hour=6,
        timezone="America/New_York",
    )
    with patch("web.services.login_scheduler.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 2, 0, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = next_login_time(user)

    assert result is not None
    # bumps to Jan 3 06:00 ET = Jan 3 11:00 UTC
    assert result == datetime(2026, 1, 3, 11, 0, 0)


def test_grace_window_rolls_forward_overdue():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=1,
        preferred_hour=9,
        timezone="America/New_York",
    )
    with patch("web.services.login_scheduler.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 10, 20, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = next_login_time(user)

    assert result is not None
    assert result > datetime(2026, 1, 10, 13, 0, 0)
    assert result.hour == 14  # 9 AM ET = 14:00 UTC
    assert result.minute == 0


def test_within_grace_window_does_not_roll():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=1,
        preferred_hour=9,
        timezone="America/New_York",
    )
    # now is only 30min past preferred, within 1h grace
    with patch("web.services.login_scheduler.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 2, 14, 30, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = next_login_time(user)

    assert result is not None
    assert result == datetime(2026, 1, 2, 14, 0, 0)


def test_utc_timezone_preferred_hour():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=5,
        preferred_hour=15,
        timezone="UTC",
    )
    with patch("web.services.login_scheduler.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 2, 0, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = next_login_time(user)

    assert result is not None
    assert result.hour == 15
    assert result.minute == 0


def test_preferred_hour_without_timezone_uses_plain_anchor():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=10,
        preferred_hour=9,
        timezone=None,
    )
    result = next_login_time(user)
    assert result == datetime(2026, 1, 11, 12, 0, 0)


def test_timezone_without_preferred_hour_uses_plain_anchor():
    user = make_user(
        last_login=datetime(2026, 1, 1, 12, 0, 0),
        login_cadence_days=10,
        preferred_hour=None,
        timezone="America/New_York",
    )
    result = next_login_time(user)
    assert result == datetime(2026, 1, 11, 12, 0, 0)



def test_reminders_skip_when_smtp_not_configured(app):
    with patch("web.services.login_scheduler.email_notifier") as mock_en:
        mock_en.is_configured.return_value = False
        send_login_reminders(app)
        mock_en.send_login_reminder.assert_not_called()


def test_reminders_skip_opted_out_users(app):
    cred = EncryptedCredential(
        vt_email="opted-out@vt.edu",
        encrypted_key="dummy",
        last_login=datetime.utcnow() + timedelta(hours=12),
        email_opt_in=False,
    )
    db.session.add(cred)
    db.session.commit()

    with patch("web.services.login_scheduler.email_notifier") as mock_en:
        mock_en.is_configured.return_value = True
        send_login_reminders(app)
        mock_en.send_login_reminder.assert_not_called()


def test_reminders_send_within_24h_window(app):
    next_time = datetime.utcnow() + timedelta(hours=12)
    cred = EncryptedCredential(
        vt_email="due-soon@vt.edu",
        encrypted_key="dummy",
        last_login=next_time - timedelta(days=25),
        email_opt_in=True,
    )
    db.session.add(cred)
    db.session.commit()

    with patch("web.services.login_scheduler.email_notifier") as mock_en:
        mock_en.is_configured.return_value = True
        mock_en.send_login_reminder.return_value = True
        send_login_reminders(app)
        mock_en.send_login_reminder.assert_called_once()


def test_reminders_dedup_already_notified(app):
    next_time = datetime.utcnow() + timedelta(hours=12)
    cred = EncryptedCredential(
        vt_email="notified@vt.edu",
        encrypted_key="dummy",
        last_login=next_time - timedelta(days=25),
        email_opt_in=True,
        last_notification_sent=datetime.utcnow(),
    )
    db.session.add(cred)
    db.session.commit()

    with patch("web.services.login_scheduler.email_notifier") as mock_en:
        mock_en.is_configured.return_value = True
        send_login_reminders(app)
        mock_en.send_login_reminder.assert_not_called()
