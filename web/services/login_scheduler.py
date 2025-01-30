from datetime import datetime, timedelta
import schedule
import time
from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential
from flask import Flask

class VTLoginScheduler:
    def __init__(self):
        """Initialize Flask app and database connection."""
        self.app = Flask(__name__)
        db_path = "web/instance/encrypted_credentials.db"
        self.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(self.app)
        self.kms_manager = KMSManager()

    def process_user(self, credential):
        """Decrypt credentials and perform Google login."""
        decrypted = self.kms_manager.decrypt(credential.encrypted_key)
        email, username, password = decrypted.split(",")

        login_bot = GoogleLogin()
        success = login_bot.login(email, username, password)

        if success:
            credential.last_login = datetime.utcnow()
            db.session.commit()
            print(f"Successfully logged in for user: {email}.")
        else:
            print(f"Failed login attempt for user: {email}.")

    def schedule_users(self):
        """Schedule periodic logins for users."""
        with self.app.app_context():
            users = EncryptedCredential.query.all()

            for user in users:
                now = datetime.utcnow()
                days_since_last_login = (now - user.last_login).days if user.last_login else 25
                days_until_next_login = max(0, 25 - days_since_last_login)

                schedule_time = now + timedelta(days=days_until_next_login)
                schedule.every(25).days.do(self.process_user, user)

                print(f"Scheduled {user.vt_email} for login in {days_until_next_login} days.")

        print(f"Scheduled {len(users)} users for periodic logins.")

    def start_scheduler(self):
        """Run the scheduler in an infinite loop."""
        self.schedule_users()
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    scheduler = VTLoginScheduler()
    scheduler.start_scheduler()