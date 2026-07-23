from datetime import datetime
from unittest.mock import patch

from web.database import db
from web.models import EncryptedCredential


def test_privacy_page_loads(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200


def test_terms_page_loads(client):
    resp = client.get("/terms")
    assert resp.status_code == 200


def test_sms_consent_page_loads(client):
    resp = client.get("/sms-consent")
    assert resp.status_code == 200
    assert b"I consent to receive" in resp.data
    assert b"SMS text messages" in resp.data
    assert b"Terms of Service" in resp.data
    assert b"operated by Thomas Feuerbach" in resp.data
    assert b"proof-consent" in resp.data
    assert b"About this service" in resp.data


def test_homepage_has_business_about(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"About this service" in resp.data
    assert b"Thomas Feuerbach" in resp.data
    assert b"tfeuerbach@mac.com" in resp.data
    assert b"SMS notifications" in resp.data


def test_sample_dashboard_shows_unchecked_sms_consent(client):
    resp = client.get("/sample-dashboard")
    assert resp.status_code == 200
    assert b'data-sample-mode="true"' in resp.data
    assert b"sms-consent-checkbox" in resp.data
    # Consent checkbox must not be pre-checked on the public sample
    assert b'id="sms-consent-checkbox" checked' not in resp.data
    assert b"Phone number" in resp.data


def test_submit_missing_fields(client):
    resp = client.post("/submit", json={"vt_email": "test@vt.edu"})
    assert resp.status_code == 400
    assert "required" in resp.get_json()["error"].lower()


def test_submit_empty_username(client):
    resp = client.post("/submit", json={"vt_email": "test@vt.edu", "vt_username": "", "vt_password": "pw"})
    assert resp.status_code == 400


def test_submit_non_vt_email(client):
    resp = client.post("/submit", json={"vt_email": "user@gmail.com", "vt_username": "user", "vt_password": "pw"})
    assert resp.status_code == 400
    assert "virginia tech" in resp.get_json()["error"].lower()


@patch("web.routes.form_routes.smtp_configured", return_value=False)
def test_submit_test_account_shortcut(mock_smtp, client):
    resp = client.post(
        "/submit", json={"vt_email": "test@vt.edu", "vt_username": "testuser", "vt_password": "testuser"}
    )
    assert resp.status_code == 200

    cred = EncryptedCredential.query.filter_by(vt_email="test@vt.edu").first()
    assert cred is not None
    assert cred.encrypted_key == "TEST_ACCOUNT_NO_REAL_CREDENTIALS"


@patch("web.routes.form_routes.smtp_configured", return_value=False)
def test_submit_test_account_updates_existing(mock_smtp, client):
    cred = EncryptedCredential(
        vt_email="test@vt.edu",
        encrypted_key="TEST_ACCOUNT_NO_REAL_CREDENTIALS",
        created_at=datetime.utcnow(),
        last_login=datetime(2020, 1, 1),
    )
    db.session.add(cred)
    db.session.commit()

    resp = client.post(
        "/submit", json={"vt_email": "test@vt.edu", "vt_username": "testuser", "vt_password": "testuser"}
    )
    assert resp.status_code == 200

    cred = EncryptedCredential.query.filter_by(vt_email="test@vt.edu").first()
    assert cred.last_login.year > 2020


@patch("web.routes.form_routes.smtp_configured", return_value=False)
def test_submit_test_account_sets_session(mock_smtp, client):
    client.post("/submit", json={"vt_email": "test@vt.edu", "vt_username": "testuser", "vt_password": "testuser"})
    with client.session_transaction() as sess:
        assert sess["authenticated_email"] == "test@vt.edu"
