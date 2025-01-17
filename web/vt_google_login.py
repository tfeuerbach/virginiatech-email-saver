import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential
from flask import Flask
import schedule
import os
import sys

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Flask app setup for database access
app = Flask(__name__)
db_path = os.path.abspath("web/instance/encrypted_credentials.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

kms_manager = KMSManager()

# Selenium setup
service = Service("/usr/local/bin/chromedriver")
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--headless")  # Run in headless mode for automation
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--window-size=1920,1080")
options.binary_location = "/snap/bin/chromium"

def login_to_google(email, username, password):
    """Automate login to Gmail."""
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # Step 1: Go to Gmail
        driver.get("https://mail.google.com")
        wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(email)
        wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()

        # Step 2: Enter VT username
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)

        # Step 3: Enter VT password
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

        # Step 4: Handle Duo 2FA
        print("Waiting for Duo push notification. Approve it on your phone.")
        for _ in range(24):  # Check every 5 seconds for up to 120 seconds
            time.sleep(5)
            current_url = driver.current_url

            # Check if "Yes, this is my device" prompt appears
            if "duosecurity.com" in current_url:
                try:
                    yes_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Yes, this is my device')]")))
                    yes_button.click()
                    print("Clicked 'Yes, this is my device'.")
                except Exception as e:
                    print(f"Error handling 'Yes, this is my device': {e}")

            # Check if login is complete (redirected to Gmail)
            if "mail.google.com" in current_url:
                print(f"Login successful for {email}!")
                return True

        print(f"Duo push not accepted for {email}.")
        return False

    except Exception as e:
        print(f"Error logging in for {email}: {e}")
        return False

    finally:
        driver.quit()


def process_user(credential):
    """Decrypt credentials and log in for a single user."""
    decrypted = kms_manager.decrypt(credential.encrypted_key)
    email, username, password = decrypted.split(",")
    success = login_to_google(email, username, password)

    if success:
        print(f"Successfully logged in for user: {email}.")
    else:
        print(f"Failed login attempt for user: {email}.")

def schedule_users():
    """Schedule logins for all users in the database."""
    with app.app_context():
        users = EncryptedCredential.query.all()

        for user in users:
            # Calculate the next login time based on created_at
            now = datetime.utcnow()
            days_since_created = (now - user.created_at).days
            days_until_next_login = max(0, 25 - days_since_created)

            schedule_time = now + timedelta(days=days_until_next_login)
            schedule.every(25).days.do(process_user, user)

            print(f"Scheduled {user.vt_email} for login in {days_until_next_login} days.")

    print(f"Scheduled {len(users)} users for periodic logins.")

if __name__ == "__main__":
    # Process the initial login upon submission
    with app.app_context():
        users = EncryptedCredential.query.all()
        for user in users:
            process_user(user)

    # Schedule periodic logins
    schedule_users()

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)