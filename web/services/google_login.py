from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import os

CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")

class GoogleLogin:
    def __init__(self):
        """Set up headless Chrome for automated login."""
        self.service = Service(CHROMEDRIVER_PATH)
        self.options = Options()

        self.options.binary_location = CHROME_BIN
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--remote-debugging-port=9222")

        self.driver = None

    def start_browser(self):
        self.driver = webdriver.Chrome(service=self.service, options=self.options)

    def update_progress(self, step):
        """Ping the progress endpoint so the frontend can show animations."""
        try:
            requests.post("http://127.0.0.1:5000/update_progress", json={"step": step})
        except Exception as e:
            print(f"Failed to send progress update: {e}")

    def login(self, email, username, password):
        """Drive through Google -> VT CAS -> Duo and return success/failure."""
        self.start_browser()
        wait = WebDriverWait(self.driver, 20)

        try:
            self.update_progress(1)
            self.driver.get("https://mail.google.com")
            self.update_progress(2)

            # Enter email on Google's page
            wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(email)
            wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()
            time.sleep(2)

            # Check for Google-side errors
            try:
                error_element = self.driver.find_element(By.XPATH, "//*[contains(@class, 'error') or contains(@jsname, 'B34EJ')]")
                if error_element.is_displayed():
                    error_text = error_element.text
                    print(f"Error detected on accounts.google.com: {error_text}")
                    return {"success": False, "error": error_text}
            except:
                pass

            # Enter VT CAS credentials
            wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
            wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()
            time.sleep(2)

            # Check for bad password
            try:
                error_element = self.driver.find_element(By.ID, "error")
                if error_element.is_displayed():
                    error_text = error_element.text
                    print(f"Login error: {error_text}")
                    return {"success": False, "error": error_text}
            except:
                pass

            # Wait for Duo 2FA
            self.update_progress(3)
            print("Waiting for Duo push notification...")

            duo_prompt_handled = False

            for _ in range(24):  # poll every 5s for up to 2 minutes
                time.sleep(5)
                current_url = self.driver.current_url

                # Auto-click "Yes, this is my device" if it shows up
                if "duosecurity.com" in current_url and not duo_prompt_handled:
                    try:
                        yes_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Yes, this is my device')]")))
                        yes_button.click()
                        duo_prompt_handled = True
                        print("Clicked 'Yes, this is my device'.")
                    except Exception as e:
                        print(f"Error handling Duo prompt: {e}")

                # We're in Gmail — login worked
                if "mail.google.com" in current_url:
                    self.update_progress(4)
                    print(f"Login successful for {email}!")
                    return {"success": True}

            print(f"Duo push not accepted for {email}.")
            return {"success": False, "error": "Duo push not accepted."}

        except Exception as e:
            print(f"Error logging in for {email}: {e}")
            return {"success": False, "error": str(e)}

        finally:
            self.driver.quit()
