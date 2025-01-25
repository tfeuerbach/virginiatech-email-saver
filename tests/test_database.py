import pytest
from web.app import create_app
from web.database import db
from web.models import EncryptedCredential

@pytest.fixture(scope="module")
def app_context():
    app = create_app()  # Replace this with your app factory if using one
    with app.app_context():
        yield app

@pytest.fixture
def init_db(app_context):
    # Setup: Create tables and add dummy data
    db.create_all()  # Create all tables
    yield
    # Teardown: Drop all tables
    db.session.remove()
    db.drop_all()

def test_database_connection(init_db):
    # Test the database connection
    assert db.session is not None

def test_add_new_entry(init_db):
    # Test adding a new entry to the database
    entry = EncryptedCredential(vt_email='test@vt.edu', encrypted_key='dummy_key')
    db.session.add(entry)
    db.session.commit()

    result = EncryptedCredential.query.filter_by(vt_email='test@vt.edu').first()
    assert result is not None
    assert result.vt_email == 'test@vt.edu'
    assert result.encrypted_key == 'dummy_key'
