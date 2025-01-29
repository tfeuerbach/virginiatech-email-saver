from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests

class GoogleLogin:
    def __init__(self, chrome_driver_path="/usr/local/bin/chromedriver"):
        """Initialize Selenium WebDriver with Chrome options."""
        self.service = Service(chrome_driver_path)
        self.options = Options()
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        # self.options.add_argument("--headless")  # Uncomment to run in headless mode
        self.options.add_argument("--remote-debugging-port=9222")
        self.options.add_argument("--window-size=1920,1080")
        self.options.binary_location = "/snap/bin/chromium"
        self.driver = None

    def start_browser(self):
        """Start a new Selenium browser session."""
        self.driver = webdriver.Chrome(service=self.service, options=self.options)

    def update_progress(self, step):
        """Send progress updates to the server."""
        try:
            requests.post("http://127.0.0.1:5000/update_progress", json={"step": step})
        except Exception as e:
            print(f"Failed to send progress update: {e}")

    def login(self, email, username, password):
        """Automate login to Gmail."""
        self.start_browser()
        wait = WebDriverWait(self.driver, 20)

        try:
            # Step 1: Store credentials
            self.update_progress(1)
            self.driver.get("https://mail.google.com")
            self.update_progress(2)

            # Step 2: Enter email and continue
            wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(email)
            wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()
            time.sleep(2)

            # Step 3: Check for error messages
            try:
                error_element = self.driver.find_element(By.XPATH, "//*[contains(@class, 'error') or contains(@jsname, 'B34EJ')]")
                if error_element.is_displayed():
                    error_text = error_element.text
                    print(f"Error detected on accounts.google.com: {error_text}")
                    return {"success": False, "error": error_text}
            except:
                pass  # No error, proceed

            # Step 4: Enter VT username and password
            wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
            wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()
            time.sleep(2)

            # Step 5: Check for "Invalid username or password"
            try:
                error_element = self.driver.find_element(By.ID, "error")
                if error_element.is_displayed():
                    error_text = error_element.text
                    print(f"Login error: {error_text}")
                    return {"success": False, "error": error_text}
            except:
                pass  # No error, continue

            # Step 6: Handle Duo 2FA
            self.update_progress(3)
            print("Waiting for Duo push notification...")

            duo_prompt_handled = False

            for _ in range(24):  # Check every 5 seconds for up to 120 seconds
                time.sleep(5)
                current_url = self.driver.current_url

                # Handle "Yes, this is my device" Duo Security prompt
                if "duosecurity.com" in current_url and not duo_prompt_handled:
                    try:
                        yes_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Yes, this is my device')]")))
                        yes_button.click()
                        duo_prompt_handled = True
                        print("Clicked 'Yes, this is my device'.")
                    except Exception as e:
                        print(f"Error handling Duo prompt: {e}")

                # Check if login was successful (redirect to Gmail inbox)
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
