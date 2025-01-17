from .database import db

class EncryptedCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vt_email = db.Column(db.String(100), nullable=False)
    encrypted_key = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<EncryptedCredential {self.vt_email}>"
