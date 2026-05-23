import pytest

from web import create_app
from web.database import db as _db

TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "WTF_CSRF_ENABLED": False,
    "SECRET_KEY": "test-secret",
}


@pytest.fixture
def app(monkeypatch):
    """Create an app with an in-memory SQLite DB and CSRF disabled."""
    monkeypatch.setenv("TESTING", "1")
    app = create_app(test_config=TEST_CONFIG)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client with CSRF disabled (for route logic tests)."""
    return app.test_client()


@pytest.fixture
def csrf_app(monkeypatch):
    """Create an app with CSRF enabled (for CSRF-specific tests)."""
    monkeypatch.setenv("TESTING", "1")
    app = create_app(test_config={**TEST_CONFIG, "WTF_CSRF_ENABLED": True})
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    """Flask test client with CSRF enabled."""
    return csrf_app.test_client()
