from datetime import datetime
from unittest.mock import patch

from web.database import db
from web.models import EncryptedCredential


def seed_user(email="test@vt.edu"):
    cred = EncryptedCredential(
        vt_email=email,
        encrypted_key="dummy_encrypted_key",
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )
    db.session.add(cred)
    db.session.commit()
    return cred


mock_decrypt = patch(
    "web.routes.dashboard_routes.kms_manager.decrypt",
    return_value="test@vt.edu,testuser,testpassword",
)


def login_user(client, email="test@vt.edu"):
    with client.session_transaction() as sess:
        sess["authenticated_email"] = email



def test_index_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_dashboard_redirects_without_session(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_processing_redirects_without_session(client):
    resp = client.get("/processing")
    assert resp.status_code == 302


def test_get_progress_rejects_without_session(client):
    resp = client.get("/get_progress")
    assert resp.status_code == 401


def test_update_cadence_rejects_without_session(client):
    resp = client.post("/update_cadence", json={"login_cadence_days": 30})
    assert resp.status_code == 401


def test_scheduler_status_rejects_without_session(client):
    resp = client.get("/scheduler_status")
    assert resp.status_code == 401


def test_schedule_logins_rejects_without_session(client):
    resp = client.post("/schedule_logins")
    assert resp.status_code == 401



@mock_decrypt
def test_dashboard_loads_with_session(mock_dec, client):
    seed_user()
    login_user(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"test@vt.edu" in resp.data


def test_dashboard_clears_session_for_unknown_email(client):
    login_user(client, "nonexistent@vt.edu")
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_processing_loads_with_session(client):
    login_user(client)
    resp = client.get("/processing")
    assert resp.status_code == 200


def test_get_progress_works_with_session(client):
    login_user(client)
    resp = client.get("/get_progress")
    assert resp.status_code == 200
    assert "step" in resp.get_json()



@mock_decrypt
def test_logout_clears_session(mock_dec, client):
    seed_user()
    login_user(client)
    assert client.get("/dashboard").status_code == 200
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302



def test_update_cadence_valid(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 45})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["login_cadence_days"] == 45


def test_update_cadence_too_low(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 0})
    assert resp.status_code == 400


def test_update_cadence_too_high(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 91})
    assert resp.status_code == 400


def test_update_cadence_not_a_number(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": "banana"})
    assert resp.status_code == 400


def test_update_cadence_missing_field(client):
    seed_user()
    login_user(client)
    resp = client.post("/update_cadence", json={})
    assert resp.status_code == 400



@patch("web.routes.schedule_routes.hourly_check")
def test_schedule_logins_success(mock_check, client):
    seed_user()
    login_user(client)
    resp = client.post("/schedule_logins")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "status" in data
    mock_check.assert_called_once()


def test_scheduler_status_success(client):
    seed_user()
    login_user(client)
    resp = client.get("/scheduler_status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "running" in data
    assert "users_checked" in data
