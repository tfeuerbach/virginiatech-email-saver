# Virginia Tech Gmail Login Automation

This project is a Flask-based web application that automates Virginia Tech Gmail logins to keep accounts active. 
It securely encrypts user credentials and automates the entire login process, including handling Duo 2FA prompts.

## Features

- **Secure Credential Storage**: User credentials are encrypted using AWS KMS before being stored in the database.
- **Automated Monthly Logins**: The app automatically logs into Gmail and Virginia Tech's SSO portal using Selenium.
- **Handles Duo 2FA**: Automatically detects and handles Duo Security prompts, including "Yes, this is my device."
- **Web Dashboard**: A simple interface to submit credentials and view the last successful login.
- **Configurable Environment**: Supports both development and production configurations, allowing seamless deployment.
- **Testing Suite**: Includes both back-end (Python) and front-end (JavaScript) tests for reliability.

## Development vs. Production Configuration

This app supports both **development** and **production** environments using different configurations.

**Development Mode (Default)**
- Uses **SQLite** for easy local testing.
- Flask runs in debug mode with automatic reloading.

**Production Mode**
- Uses **PostgreSQL** for database storage.
- Configured for Docker deployment with `docker-compose`.
- Flask runs with `gunicorn` for better performance.

## Prerequisites

- Python 3.11+
- Flask, Flask-SQLAlchemy
- Selenium WebDriver + Google Chrome
- AWS KMS (for secure credential encryption)
- `chromedriver` installed and correctly configured
- Node.js (for JavaScript testing)
- Docker + Docker Compose (for production)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd virginiatech-email-saver
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv .envs/vt_login
   source .envs/vt_login/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install JavaScript dependencies**:
   ```bash
   npm install
   ```

5. **Configure environment variables**:
   Copy `.env.example` to `.env` and update:
   ```
   AWS_ACCESS_KEY_ID=<your-access-key>
   AWS_SECRET_ACCESS_KEY=<your-secret-key>
   KMS_KEY_ID=arn:aws:kms:<region>:<account-id>:key/<key-id>
   FLASK_ENV=development  # Change to production when deploying
   DATABASE_URL=sqlite:///instance/encrypted_credentials.db
   ```

6. **Ensure `chromedriver` is installed and matches your Chrome version**:
   ```bash
   chromedriver --version
   google-chrome --version
   ```

7. **Start the Flask app (Development Mode)**:
   ```bash
   flask --app web run
   ```

8. **Run in Docker (Production Mode)**:
   ```bash
   docker-compose up --build -d
   ```

## Usage

1. Open the app in your browser:
   ```
   http://127.0.0.1:5000
   ```

2. Submit your **Virginia Tech email, username, and password**.
   - Credentials are **encrypted with AWS KMS**.
   - The app **automates Gmail login using Selenium**.
   - **Handles Duo push authentication** automatically.

3. View the **last successful login** in the dashboard.

4. To check stored credentials:
   ```bash
   sqlite3 instance/encrypted_credentials.db
   SELECT * FROM encrypted_credential;
   ```

## Testing

### Python Tests
- Unit and integration tests for back-end functionality.
   ```bash
   pytest
   ```

### JavaScript Tests
- Uses Vitest for front-end testing.
   ```bash
   npm run test
   ```

## Future Enhancements

- **Automated login scheduling** (every 25 days).
- **Email notifications** for login status.
- **Enhanced UI/UX** for a better user experience.
- **Support for additional 2FA authentication methods**.

## Contributing

Contributions are welcome Feel free to fork the repository, submit pull requests, or suggest improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.