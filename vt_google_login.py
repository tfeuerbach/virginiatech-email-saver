import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC  

# Your credentials
GMAIL_EMAIL = "thomashf@vt.edu"
VT_USERNAME = "thomashf"
VT_PASSWORD = "Virginiatechhokies4u!1"

# Enable detailed ChromeDriver logs
service = Service("/usr/local/bin/chromedriver", service_args=["--verbose", "--log-path=chromedriver.log"])

# Set up Chrome options
options = Options()
# Comment out "--headless" to see the browser in action
# options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")

# Point to the Snap-installed Chromium binary
options.binary_location = "/snap/bin/chromium"

def login_to_google():
    # Start the browser with ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # Step 1: Go to Gmail
        driver.get("https://mail.google.com")
        time.sleep(2)

        # Step 2: Enter Gmail email and click "Next"
        wait.until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(GMAIL_EMAIL)
        wait.until(EC.element_to_be_clickable((By.ID, "identifierNext"))).click()
        time.sleep(3)

        # Step 3: Enter VT username
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(VT_USERNAME)

        # Step 4: Enter VT password
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(VT_PASSWORD)

        # Step 5: Click the "Sign in" button
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

        # Step 6: Wait for Duo push approval
        print("Waiting for Duo push notification. Approve it on your phone.")
        for i in range(24):  # Check every 5 seconds, up to 120 seconds total
            time.sleep(5)
            current_url = driver.current_url
            print(f"Current URL: {current_url}")

            # If redirected to Duo Security, check for "Yes, this is my device" prompt
            if "duosecurity.com" in current_url:
                try:
                    yes_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Yes, this is my device')]")))
                    yes_button.click()
                    print("Selected 'Yes, this is my device'.")
                    break
                except:
                    print("No 'Yes, this is my device' prompt found.")

            # Check if login is complete (redirected to Gmail)
            if "mail.google.com" in current_url:
                print("Duo push accepted! Proceeding...")
                break
        else:
            print("Duo push not accepted within 120 seconds.")

        print("Login successful!")
        time.sleep(10)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    login_to_google()
