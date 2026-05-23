def auth_session(csrf_client):
    with csrf_client.session_transaction() as sess:
        sess["authenticated_email"] = "test@vt.edu"


def test_submit_rejected_without_csrf_token(csrf_client):
    resp = csrf_client.post(
        "/submit",
        json={"vt_email": "test@vt.edu", "vt_username": "test", "vt_password": "pw"},
    )
    assert resp.status_code == 400


def test_update_cadence_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_cadence", json={"login_cadence_days": 30})
    assert resp.status_code == 400


def test_schedule_logins_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/schedule_logins")
    assert resp.status_code == 400


def test_update_timezone_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_timezone", json={"timezone": "UTC"})
    assert resp.status_code == 400


def test_update_preferred_time_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_preferred_time", json={"preferred_hour": 9})
    assert resp.status_code == 400


def test_update_notification_email_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_notification_email", json={"notification_email": "a@b.com"})
    assert resp.status_code == 400


def test_update_email_opt_in_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_email_opt_in", json={"email_opt_in": True})
    assert resp.status_code == 400


def test_update_sms_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/update_sms_preferences", json={"sms_opt_in": True, "phone_number": "5551234567"})
    assert resp.status_code == 400


def test_delete_account_rejected_without_csrf_token(csrf_client):
    auth_session(csrf_client)
    resp = csrf_client.post("/delete_account")
    assert resp.status_code == 400
