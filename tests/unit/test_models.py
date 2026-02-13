from web.database import db
from web.models import (
    EncryptedCredential,
    DEFAULT_CADENCE_DAYS,
    MIN_CADENCE_DAYS,
    MAX_CADENCE_DAYS,
)


def test_model_repr():
    credential = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy")
    assert repr(credential) == "<EncryptedCredential(vt_email='test@vt.edu')>"


def test_cadence_defaults(app):
    """The default cadence should be applied when a row is inserted."""
    cred = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy")
    db.session.add(cred)
    db.session.flush()
    assert cred.login_cadence_days == DEFAULT_CADENCE_DAYS


def test_cadence_constants():
    assert MIN_CADENCE_DAYS == 1
    assert MAX_CADENCE_DAYS == 90
    assert MIN_CADENCE_DAYS < DEFAULT_CADENCE_DAYS < MAX_CADENCE_DAYS
