from web.database import db
from web.models import EncryptedCredential


def test_database_connection(app):
    assert db.session is not None


def test_add_and_query_entry(app):
    entry = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy_key")
    db.session.add(entry)
    db.session.commit()

    result = EncryptedCredential.query.filter_by(vt_email="test@vt.edu").first()
    assert result is not None
    assert result.vt_email == "test@vt.edu"
    assert result.encrypted_key == "dummy_key"
    assert result.login_cadence_days == 25
