from datetime import datetime
from unittest.mock import patch

from web.database import db
from web.models import EncryptedCredential


def seed_user(email="test@vt.edu", **overrides):
    defaults = dict(
        vt_email=email,
        encrypted_key="dummy_encrypted_key",
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )
    defaults.update(overrides)
    cred = EncryptedCredential(**defaults)
    db.session.add(cred)
    db.session.commit()
    return cred


def login_user(client, email="test@vt.edu"):
    with client.session_transaction() as sess:
        sess["authenticated_email"] = email


def test_update_timezone_rejects_without_session(client):
    resp = client.post("/update_timezone", json={"timezone": "UTC"})
    assert resp.status_code == 401


def test_update_timezone_requires_value(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_timezone", json={"timezone": ""})
    assert resp.status_code == 400


def test_update_timezone_rejects_invalid(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_timezone", json={"timezone": "Not/A/Zone"})
    assert resp.status_code == 400


def test_update_timezone_valid(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_timezone", json={"timezone": "America/New_York"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["timezone"] == "America/New_York"
    assert data["timezone_label"] == "Eastern"


def test_update_timezone_accepts_any_iana(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_timezone", json={"timezone": "Asia/Tokyo"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["timezone"] == "Asia/Tokyo"
    assert data["timezone_label"] == "Asia/Tokyo"


def test_update_timezone_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/update_timezone", json={"timezone": "UTC"})
    assert resp.status_code == 404


def test_preferred_time_rejects_without_session(client):
    resp = client.post("/update_preferred_time", json={"preferred_hour": 9})
    assert resp.status_code == 401


def test_preferred_time_clears_with_empty(client):
    seed_user(preferred_hour=9, timezone="UTC")
    login_user(client)
    resp = client.post("/update_preferred_time", json={"preferred_hour": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["preferred_hour"] is None


def test_preferred_time_clears_with_none(client):
    seed_user(preferred_hour=9, timezone="UTC")
    login_user(client)
    resp = client.post("/update_preferred_time", json={"preferred_hour": None})
    assert resp.status_code == 200
    assert resp.get_json()["preferred_hour"] is None


def test_preferred_time_rejects_non_numeric(client):
    seed_user(timezone="UTC")
    login_user(client)
    resp = client.post("/update_preferred_time", json={"preferred_hour": "noon"})
    assert resp.status_code == 400


def test_preferred_time_rejects_out_of_range(client):
    seed_user(timezone="UTC")
    login_user(client)
    for bad in [-1, 24, 100]:
        resp = client.post("/update_preferred_time", json={"preferred_hour": bad})
        assert resp.status_code == 400, f"Expected 400 for hour={bad}"


def test_preferred_time_requires_timezone_first(client):
    seed_user(timezone=None)
    login_user(client)
    resp = client.post("/update_preferred_time", json={"preferred_hour": 9})
    assert resp.status_code == 400
    assert "timezone" in resp.get_json()["error"].lower()


def test_preferred_time_valid(client):
    seed_user(timezone="America/Chicago")
    login_user(client)
    resp = client.post("/update_preferred_time", json={"preferred_hour": 14})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["preferred_hour"] == 14


def test_preferred_time_boundary_values(client):
    seed_user(timezone="UTC")
    login_user(client)
    for hour in [0, 23]:
        resp = client.post("/update_preferred_time", json={"preferred_hour": hour})
        assert resp.status_code == 200
        assert resp.get_json()["preferred_hour"] == hour


def test_preferred_time_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/update_preferred_time", json={"preferred_hour": 9})
    assert resp.status_code == 404


def test_notification_email_rejects_without_session(client):
    resp = client.post("/update_notification_email", json={"notification_email": "a@b.com"})
    assert resp.status_code == 401


def test_notification_email_reset_to_vt(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_notification_email", json={"notification_email": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_custom"] is False
    assert data["notification_email"] == "test@vt.edu"


def test_notification_email_same_as_vt_resets(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_notification_email", json={"notification_email": "test@vt.edu"})
    assert resp.status_code == 200
    assert resp.get_json()["is_custom"] is False


def test_notification_email_custom_valid(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_notification_email", json={"notification_email": "me@gmail.com"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_custom"] is True
    assert data["notification_email"] == "me@gmail.com"


def test_notification_email_invalid_format(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_notification_email", json={"notification_email": "not-an-email"})
    assert resp.status_code == 400


def test_notification_email_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/update_notification_email", json={"notification_email": "a@b.com"})
    assert resp.status_code == 404


def test_email_opt_in_rejects_without_session(client):
    resp = client.post("/update_email_opt_in", json={"email_opt_in": True})
    assert resp.status_code == 401


def test_email_opt_in_enable(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_email_opt_in", json={"email_opt_in": True})
    assert resp.status_code == 200
    assert resp.get_json()["email_opt_in"] is True


def test_email_opt_in_disable(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_email_opt_in", json={"email_opt_in": False})
    assert resp.status_code == 200
    assert resp.get_json()["email_opt_in"] is False


def test_email_opt_in_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/update_email_opt_in", json={"email_opt_in": True})
    assert resp.status_code == 404


def test_sms_rejects_without_session(client):
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "5551234567"})
    assert resp.status_code == 401


@patch("web.routes.dashboard_routes.sms_notifier")
def test_sms_opt_in_valid_phone(mock_sms, client):
    mock_sms.is_configured.return_value = False
    seed_user()
    login_user(client)
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "(555) 123-4567"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["sms_opt_in"] is True
    assert data["phone_number"] == "+15551234567"


def test_sms_opt_in_invalid_phone(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "123"})
    assert resp.status_code == 400


@patch("web.routes.dashboard_routes.sms_notifier")
def test_sms_opt_in_sends_confirmation(mock_sms, client):
    mock_sms.is_configured.return_value = True
    seed_user()
    login_user(client)
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "5551234567"})
    assert resp.status_code == 200
    mock_sms.send_opt_in_confirmation.assert_called_once_with("+15551234567")


@patch("web.routes.dashboard_routes.sms_notifier")
def test_sms_opt_out(mock_sms, client):
    seed_user(phone_number="+15551234567", sms_opt_in=True)
    login_user(client)
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": False})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["sms_opt_in"] is False
    assert data["phone_number"] == ""


def test_sms_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "5551234567"})
    assert resp.status_code == 404


def test_calendar_redirects_without_session(client):
    resp = client.get("/download_calendar")
    assert resp.status_code == 302


def test_calendar_redirects_missing_user(client):
    login_user(client, "ghost@vt.edu")
    resp = client.get("/download_calendar")
    assert resp.status_code == 302


def test_calendar_returns_ics(client):
    seed_user()
    login_user(client)
    resp = client.get("/download_calendar")
    assert resp.status_code == 200
    assert resp.content_type == "text/calendar; charset=utf-8"
    assert b"BEGIN:VCALENDAR" in resp.data
    assert b"RRULE:FREQ=DAILY" in resp.data
    assert b"VALARM" in resp.data


def test_calendar_interval_matches_cadence(client):
    seed_user(login_cadence_days=15)
    login_user(client)
    resp = client.get("/download_calendar")
    assert b"INTERVAL=15" in resp.data


def test_calendar_uid_contains_email(client):
    seed_user()
    login_user(client)
    resp = client.get("/download_calendar")
    assert b"vtemailsaver-test-at-vt.edu" in resp.data


def test_delete_account_rejects_without_session(client):
    resp = client.post("/delete_account")
    assert resp.status_code == 401


def test_delete_account_removes_user(client):
    seed_user()
    login_user(client)
    resp = client.post("/delete_account")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["redirect"] == "/"
    assert EncryptedCredential.query.filter_by(vt_email="test@vt.edu").first() is None


def test_delete_account_clears_session(client):
    seed_user()
    login_user(client)
    client.post("/delete_account")
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_delete_account_user_not_found(client):
    login_user(client, "ghost@vt.edu")
    resp = client.post("/delete_account")
    assert resp.status_code == 404
