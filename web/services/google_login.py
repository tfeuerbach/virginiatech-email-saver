import logging
import os
import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
HEADLESS = os.getenv("SELENIUM_HEADLESS", "true").lower() in ("true", "1", "yes")
INTERNAL_URL = os.getenv("INTERNAL_URL", "http://127.0.0.1:5000")


class GoogleLogin:
    def __init__(self):
        """Set up headless Chrome."""
        self.service = Service(CHROMEDRIVER_PATH)
        self.options = Options()

        self.options.binary_location = CHROME_BIN
        if HEADLESS:
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
        """Ping the progress endpoint for frontend updates."""
        try:
            requests.post(f"{INTERNAL_URL}/update_progress", json={"step": step})
        except Exception as e:
            logger.warning("Failed to send progress update: %s", e)

    def login(self, email, username, password):
        """Google -> VT CAS -> Duo login flow. Returns dict with success/error."""
        self.start_browser()
        wait = WebDriverWait(self.driver, 20)

        try:
            self.update_progress(1)
            self.driver.get("https://mail.google.com")
            self.update_progress(2)

            wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(email)
            wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()

            time.sleep(1)
            try:
                error_element = self.driver.find_element(
                    By.XPATH, "//*[contains(@class, 'error') or contains(@jsname, 'B34EJ')]"
                )
                if error_element.is_displayed():
                    error_text = error_element.text
                    logger.warning("Error on accounts.google.com: %s", error_text)
                    return {"success": False, "error": error_text}
            except Exception:
                pass

            wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
            wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

            time.sleep(1)
            try:
                error_element = self.driver.find_element(By.ID, "error")
                if error_element.is_displayed():
                    error_text = error_element.text
                    logger.warning("Login error: %s", error_text)
                    return {"success": False, "error": error_text}
            except Exception:
                pass

            self.update_progress(3)
            logger.info("Waiting for Duo push notification...")

            duo_prompt_handled = False

            for _ in range(60):  # poll every 2s for up to 2 minutes
                time.sleep(2)
                current_url = self.driver.current_url

                if "duosecurity.com" in current_url and not duo_prompt_handled:
                    try:
                        yes_button = self.driver.find_element(
                            By.XPATH, "//button[contains(text(),'Yes, this is my device')]"
                        )
                        if yes_button.is_displayed():
                            yes_button.click()
                            duo_prompt_handled = True
                            logger.info("Clicked 'Yes, this is my device'.")
                    except Exception:
                        pass

                if "mail.google.com" in current_url:
                    self.update_progress(4)
                    logger.info("Login successful for %s", email)
                    return {"success": True}

            logger.warning("Duo push not accepted for %s", email)
            return {"success": False, "error": "Duo push not accepted."}

        except Exception as e:
            logger.error("Error logging in for %s: %s", email, e)
            return {"success": False, "error": str(e)}

        finally:
            self.driver.quit()
