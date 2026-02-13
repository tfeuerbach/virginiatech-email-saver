"""Test that all public routes enforce session auth correctly."""

from datetime import datetime
from unittest.mock import patch
from web.database import db
from web.models import EncryptedCredential


def _seed_user(email="test@vt.edu"):
    """Insert a test credential and return it."""
    cred = EncryptedCredential(
        vt_email=email,
        encrypted_key="dummy_encrypted_key",
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )
    db.session.add(cred)
    db.session.commit()
    return cred


# Mock KMS decrypt so we don't need real ciphertext in tests.
# The dashboard splits on "," and takes [1:], so we need at least 3 parts.
_mock_decrypt = patch(
    "web.routes.dashboard_routes.kms_manager.decrypt",
    return_value="test@vt.edu,testuser,testpassword",
)


def _login(client, email="test@vt.edu"):
    """Set the session as if the user just submitted the form."""
    with client.session_transaction() as sess:
        sess["authenticated_email"] = email


# --- Unauthenticated access ---

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


# --- Authenticated access ---

@_mock_decrypt
def test_dashboard_loads_with_session(mock_dec, client):
    _seed_user()
    _login(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"test@vt.edu" in resp.data


def test_dashboard_clears_session_for_unknown_email(client):
    _login(client, "nonexistent@vt.edu")
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_processing_loads_with_session(client):
    _login(client)
    resp = client.get("/processing")
    assert resp.status_code == 200


def test_get_progress_works_with_session(client):
    _login(client)
    resp = client.get("/get_progress")
    assert resp.status_code == 200
    assert "step" in resp.get_json()


# --- Logout ---

@_mock_decrypt
def test_logout_clears_session(mock_dec, client):
    _seed_user()
    _login(client)
    # Verify we're logged in
    assert client.get("/dashboard").status_code == 200
    # Log out
    client.get("/logout")
    # Should be kicked back now
    assert client.get("/dashboard").status_code == 302


# --- Cadence validation ---

def test_update_cadence_valid(client):
    _seed_user()
    _login(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 45})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["login_cadence_days"] == 45


def test_update_cadence_too_low(client):
    _seed_user()
    _login(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 0})
    assert resp.status_code == 400


def test_update_cadence_too_high(client):
    _seed_user()
    _login(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": 91})
    assert resp.status_code == 400


def test_update_cadence_not_a_number(client):
    _seed_user()
    _login(client)
    resp = client.post("/update_cadence", json={"login_cadence_days": "banana"})
    assert resp.status_code == 400


def test_update_cadence_missing_field(client):
    _seed_user()
    _login(client)
    resp = client.post("/update_cadence", json={})
    assert resp.status_code == 400
