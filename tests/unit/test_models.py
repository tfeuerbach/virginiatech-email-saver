from web.database import db
from web.models import (
    DEFAULT_CADENCE_DAYS,
    MAX_CADENCE_DAYS,
    MIN_CADENCE_DAYS,
    EncryptedCredential,
    SchedulerState,
)


def test_model_repr():
    credential = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy")
    assert repr(credential) == "<EncryptedCredential(vt_email='test@vt.edu')>"


def test_cadence_defaults(app):
    cred = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy")
    db.session.add(cred)
    db.session.flush()
    assert cred.login_cadence_days == DEFAULT_CADENCE_DAYS


def test_cadence_constants():
    assert MIN_CADENCE_DAYS == 1
    assert MAX_CADENCE_DAYS == 90
    assert MIN_CADENCE_DAYS < DEFAULT_CADENCE_DAYS < MAX_CADENCE_DAYS


def test_effective_notification_email_defaults_to_vt():
    cred = EncryptedCredential(vt_email="test@vt.edu", encrypted_key="dummy")
    assert cred.effective_notification_email == "test@vt.edu"


def test_effective_notification_email_uses_custom():
    cred = EncryptedCredential(
        vt_email="test@vt.edu",
        encrypted_key="dummy",
        notification_email="custom@gmail.com",
    )
    assert cred.effective_notification_email == "custom@gmail.com"


def test_scheduler_state_get_creates_row(app):
    assert db.session.get(SchedulerState, 1) is None
    state = SchedulerState.get()
    assert state is not None
    assert state.id == 1
    assert state.running is False


def test_scheduler_state_get_returns_existing(app):
    first = SchedulerState.get()
    first.running = True
    db.session.commit()
    second = SchedulerState.get()
    assert second.running is True


def test_scheduler_state_to_dict_keys(app):
    state = SchedulerState.get()
    d = state.to_dict()
    expected_keys = {
        "running",
        "last_check",
        "next_check",
        "last_check_result",
        "users_checked",
        "logins_attempted",
        "logins_succeeded",
        "notifications_sent",
    }
    assert set(d.keys()) == expected_keys


def test_scheduler_state_to_dict_defaults(app):
    d = SchedulerState.get().to_dict()
    assert d["running"] is False
    assert d["last_check"] is None
    assert d["next_check"] is None
    assert d["last_check_result"] is None
    assert d["users_checked"] == 0
    assert d["logins_attempted"] == 0
    assert d["logins_succeeded"] == 0
    assert d["notifications_sent"] == 0
