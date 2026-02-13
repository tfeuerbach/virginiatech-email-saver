"""Verify CSRF protection rejects POST requests without a token."""


def test_submit_rejected_without_csrf_token(csrf_client):
    resp = csrf_client.post(
        "/submit",
        json={"vt_email": "test@vt.edu", "vt_username": "test", "vt_password": "pw"},
    )
    assert resp.status_code == 400


def test_update_cadence_rejected_without_csrf_token(csrf_client):
    with csrf_client.session_transaction() as sess:
        sess["authenticated_email"] = "test@vt.edu"

    resp = csrf_client.post(
        "/update_cadence",
        json={"login_cadence_days": 30},
    )
    assert resp.status_code == 400


def test_schedule_logins_rejected_without_csrf_token(csrf_client):
    with csrf_client.session_transaction() as sess:
        sess["authenticated_email"] = "test@vt.edu"

    resp = csrf_client.post("/schedule_logins")
    assert resp.status_code == 400
