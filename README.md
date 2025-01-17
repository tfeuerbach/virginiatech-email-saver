# Virginia Tech Gmail Login Automation

This project is a Flask-based application designed to help users keep their Virginia Tech Gmail accounts active by automating the monthly login process. It encrypts user credentials securely and automates the login flow to Gmail and the Virginia Tech Single Sign-On (SSO) portal using Selenium.

## Features

- **Credential Encryption**: User credentials are encrypted using AWS KMS before being stored in a database.
- **Automated Login**: Selenium handles logging into Gmail and Virginia Tech's SSO portal, including handling Duo 2FA prompts.
- **Database Management**: Encrypted credentials are securely stored in an SQLite database.
- **Web Interface**: Users can submit their credentials via a simple web form.

## Prerequisites

- Python 3.11 or higher
- Flask and Flask-SQLAlchemy
- Selenium WebDriver and Chromium
- AWS KMS key for credential encryption
- `chromedriver` installed and configured

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd virginiatech-email-saver
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv .envs/vt_login
   source .envs/vt_login/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure AWS KMS:
   Add your KMS key ARN and AWS credentials to the `.env` file:
   ```
   AWS_ACCESS_KEY_ID=<your-access-key>
   AWS_SECRET_ACCESS_KEY=<your-secret-key>
   KMS_KEY_ID=arn:aws:kms:<region>:<account-id>:key/<key-id>
   ```

5. Ensure `chromedriver` is installed and available in your PATH.

6. Initialize the Flask app:
   ```bash
   python -m web.app
   ```

## Usage

1. Start the Flask app:
   ```bash
   python -m web.app
   ```

2. Open the app in your browser:
   ```
   http://127.0.0.1:5000
   ```

3. Submit your Virginia Tech email, username, and password. The app will:
   - Encrypt your credentials using AWS KMS.
   - Store them securely in the SQLite database.
   - Automate the login process using Selenium.

4. Verify the stored credentials:
   ```bash
   sqlite3 web/instance/encrypted_credentials.db
   SELECT * FROM encrypted_credential;
   ```

## Future Enhancements

- Add a periodic task scheduler to automate the login process every 25 days.
- Integrate user notifications (e.g., email reminders) for login status.
- Enhance the web interface for better user experience.

## Contributing

Feel free to fork the repository and submit pull requests. Contributions are welcome

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
