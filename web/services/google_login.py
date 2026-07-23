import logging
import os
import time
from typing import Callable

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

DUO_CODE_SELECTOR = ".code-box .code-text"
DUO_WAIT_SECONDS = 180
DUO_POLL_SECONDS = 2


def normalise_duo_code(raw: str | None) -> str | None:
    """Return a numeric Duo passcode, or None if the text isn't one."""
    code = (raw or "").strip()
    if code.isdigit() and 3 <= len(code) <= 8:
        return code
    return None


class GoogleLogin:
    def __init__(self):
        """Set up headless Chrome."""
        self.service = Service(CHROMEDRIVER_PATH)
        self.options = Options()

        self.options.binary_location = CHROME_BIN
        if HEADLESS:
            # "new" headless is less likely to be blocked by Google/CAS
            self.options.add_argument("--headless=new")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--remote-debugging-port=9222")
        self.options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)

        self.driver = None

    def start_browser(self):
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                },
            )
        except Exception as e:
            logger.debug("Could not patch navigator.webdriver: %s", e)

    def _log_page_state(self, context: str):
        """Log URL/title/snippet so empty Selenium timeouts are diagnosable."""
        if not self.driver:
            return
        try:
            url = self.driver.current_url
            title = self.driver.title
            body = ""
            try:
                body = (self.driver.find_element(By.TAG_NAME, "body").text or "")[:400]
            except Exception:
                pass
            logger.error(
                "Login stuck (%s): url=%s title=%r body_snippet=%r",
                context,
                url,
                title,
                body.replace("\n", " | "),
            )
            try:
                self.driver.save_screenshot("/tmp/login_failure.png")
                logger.error("Saved failure screenshot to /tmp/login_failure.png")
            except Exception:
                pass
        except Exception as e:
            logger.error("Could not capture page state (%s): %s", context, e)

    def update_progress(self, step, duo_code=None):
        """Ping the progress endpoint for frontend updates."""
        payload = {"step": step}
        if duo_code is not None:
            payload["duo_code"] = duo_code
        try:
            requests.post(f"{INTERNAL_URL}/update_progress", json=payload, timeout=5)
        except Exception as e:
            logger.warning("Failed to send progress update: %s", e)

    def _extract_duo_code(self) -> str | None:
        if not self.driver:
            return None
        try:
            code_el = self.driver.find_element(By.CSS_SELECTOR, DUO_CODE_SELECTOR)
            if code_el.is_displayed():
                return normalise_duo_code(code_el.text)
        except Exception:
            pass
        return None

    def _wait_for_duo(
        self,
        on_duo_code: Callable[[str], None] | None = None,
    ) -> dict:
        """Handle Duo device prompt and passcode entry."""
        self.update_progress(3)
        logger.info("Waiting for Duo verification...")

        duo_prompt_handled = False
        duo_code_sent = False
        polls = DUO_WAIT_SECONDS // DUO_POLL_SECONDS

        for _ in range(polls):
            time.sleep(DUO_POLL_SECONDS)
            current_url = self.driver.current_url

            if "duosecurity.com" in current_url:
                if not duo_prompt_handled:
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

                code = self._extract_duo_code()
                if code and not duo_code_sent:
                    self.update_progress(3, duo_code=code)
                    if on_duo_code:
                        try:
                            on_duo_code(code)
                        except Exception as e:
                            logger.warning("Duo code callback failed: %s", e)
                    duo_code_sent = True
                    logger.info("Duo verification code ready for user entry")

            if "mail.google.com" in current_url:
                self.update_progress(4)
                logger.info("Login successful")
                return {"success": True}

        if duo_code_sent:
            error = "Duo code was not entered in time."
        else:
            error = "Duo verification not completed in time."
        logger.warning(error)
        return {"success": False, "error": error}

    def login(
        self,
        email,
        username,
        password,
        on_duo_code: Callable[[str], None] | None = None,
    ):
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

            try:
                wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
            except Exception:
                self._log_page_state("waiting for VT CAS username field")
                raise

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

            return self._wait_for_duo(on_duo_code=on_duo_code)

        except Exception as e:
            self._log_page_state("unhandled exception")
            msg = str(e).strip() or type(e).__name__
            logger.error("Error logging in for %s: %s", email, msg)
            return {"success": False, "error": msg}

        finally:
            self.driver.quit()
