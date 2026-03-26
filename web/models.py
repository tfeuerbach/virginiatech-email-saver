from datetime import datetime

from web.database import db

# Cadence bounds (in days)
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
    # email reminder opt-in (defaults to on when SMTP is configured)
    email_opt_in = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    # optional override — if null, notifications go to vt_email
    notification_email = db.Column(db.String(120), nullable=True)
    # tracks when we last emailed the user a "login coming up" reminder
    last_notification_sent = db.Column(db.DateTime, nullable=True)
    # SMS notification opt-in
    phone_number = db.Column(db.String(20), nullable=True)
    sms_opt_in = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    # one-time welcome email tracking
    welcome_email_sent = db.Column(db.Boolean, nullable=False, default=False, server_default="false")

    @property
    def effective_notification_email(self):
        """Where to send reminders — custom email if set, otherwise their VT email."""
        return self.notification_email or self.vt_email

    def __repr__(self):
        return f"<EncryptedCredential(vt_email='{self.vt_email}')>"
