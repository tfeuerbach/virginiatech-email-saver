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
import requests
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
# options.add_argument("--headless")  # Uncomment to run in headless mode
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--window-size=1920,1080")
options.binary_location = "/snap/bin/chromium"

def update_progress(step):
    """Send progress updates to the server."""
    try:
        requests.post("http://127.0.0.1:5000/update_progress", json={"step": step})
    except Exception as e:
        print(f"Failed to send progress update: {e}")

def login_to_google(email, username, password):
    """Automate login to Gmail."""
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # Step 1: Start progress
        update_progress(1)  # Storing credentials

        # Step 2: Go to Gmail
        driver.get("https://mail.google.com")
        update_progress(2)  # Attempting login
        wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(email)
        wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()

        # Step 3: Enter VT username and password
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

        # Step 4: Handle Duo 2FA
        update_progress(3)  # Sending push notification
        print("Waiting for Duo push notification. Approve it on your phone.")
        duo_prompt_handled = False

        for _ in range(24):  # Check every 5 seconds for up to 120 seconds
            time.sleep(5)
            current_url = driver.current_url

            if "duosecurity.com" in current_url and not duo_prompt_handled:
                try:
                    yes_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Yes, this is my device')]")))
                    yes_button.click()
                    duo_prompt_handled = True
                    print("Clicked 'Yes, this is my device'.")
                except Exception as e:
                    print(f"Error handling Duo prompt: {e}")

            if "mail.google.com" in current_url:
                update_progress(4)  # Success
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
        credential.last_login = datetime.utcnow()
        db.session.commit()
        print(f"Successfully logged in for user: {email}.")
    else:
        print(f"Failed login attempt for user: {email}.")

def schedule_users():
    """Schedule logins for all users in the database."""
    with app.app_context():
        users = EncryptedCredential.query.all()

        for user in users:
            now = datetime.utcnow()
            days_since_last_login = (now - user.last_login).days if user.last_login else 25
            days_until_next_login = max(0, 25 - days_since_last_login)

            schedule_time = now + timedelta(days=days_until_next_login)
            schedule.every(25).days.do(process_user, user)

            print(f"Scheduled {user.vt_email} for login in {days_until_next_login} days.")

    print(f"Scheduled {len(users)} users for periodic logins.")

if __name__ == "__main__":
    with app.app_context():
        users = EncryptedCredential.query.all()
        for user in users:
            process_user(user)

    schedule_users()

    while True:
        schedule.run_pending()
        time.sleep(1)
