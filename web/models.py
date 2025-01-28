from datetime import datetime
from web.database import db

class EncryptedCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vt_email = db.Column(db.String(120), unique=True, nullable=False)
    encrypted_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<EncryptedCredential(vt_email='{self.vt_email}')>"
