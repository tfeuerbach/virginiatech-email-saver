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
    login_cadence_days = db.Column(
        db.Integer, nullable=False, default=DEFAULT_CADENCE_DAYS, server_default="25"
    )

    def __repr__(self):
        return f"<EncryptedCredential(vt_email='{self.vt_email}')>"
