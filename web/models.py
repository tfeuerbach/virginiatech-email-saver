from datetime import datetime

from web.database import db

DEFAULT_CADENCE_DAYS = 25
MIN_CADENCE_DAYS = 1
MAX_CADENCE_DAYS = 90


class EncryptedCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vt_email = db.Column(db.String(120), unique=True, nullable=False)
    encrypted_key = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    login_cadence_days = db.Column(db.Integer, nullable=False, default=DEFAULT_CADENCE_DAYS, server_default="25")
    email_opt_in = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    notification_email = db.Column(db.String(120), nullable=True)
    last_notification_sent = db.Column(db.DateTime, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    sms_opt_in = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    welcome_email_sent = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    preferred_hour = db.Column(db.Integer, nullable=True)
    timezone = db.Column(db.String(50), nullable=True)

    @property
    def effective_notification_email(self):
        return self.notification_email or self.vt_email

    def __repr__(self):
        return f"<EncryptedCredential(vt_email='{self.vt_email}')>"


class SchedulerState(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    running = db.Column(db.Boolean, nullable=False, default=False)
    last_check = db.Column(db.DateTime, nullable=True)
    next_check = db.Column(db.DateTime, nullable=True)
    last_result = db.Column(db.String(200), nullable=True)
    users_checked = db.Column(db.Integer, nullable=False, default=0)
    logins_attempted = db.Column(db.Integer, nullable=False, default=0)
    logins_succeeded = db.Column(db.Integer, nullable=False, default=0)
    notifications_sent = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def get(cls):
        state = db.session.get(cls, 1)
        if state is None:
            state = cls(id=1)
            db.session.add(state)
            db.session.commit()
        return state

    def to_dict(self):
        return {
            "running": self.running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "next_check": self.next_check.isoformat() if self.next_check else None,
            "last_check_result": self.last_result,
            "users_checked": self.users_checked,
            "logins_attempted": self.logins_attempted,
            "logins_succeeded": self.logins_succeeded,
            "notifications_sent": self.notifications_sent,
        }
