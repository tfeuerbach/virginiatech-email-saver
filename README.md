# Virginia Tech Gmail Login Automation

This project is a Flask-based web application that automates Virginia Tech Gmail logins to keep accounts active. 
It securely encrypts user credentials and automates the entire login process, including handling Duo 2FA prompts.

## Features

- **Secure Credential Storage**: User credentials are encrypted using AWS KMS before being stored in the database.
- **Automated Logins**: The app automatically logs into Gmail and Virginia Tech's SSO portal using Selenium.
- **Configurable Cadence**: Users can set their own login interval (1–90 days, defaults to 25).
- **Handles Duo 2FA**: Automatically detects and handles Duo Security prompts, including "Yes, this is my device."
- **Web Dashboard**: Session-protected interface to view login history, adjust cadence, and check scheduler status.
- **CSRF Protection**: All POST endpoints are protected against cross-site request forgery.
- **Configurable Environment**: Supports both development and production configurations.

## Development vs. Production Configuration

This app supports both **development** and **production** environments using different configurations.

**Development Mode (Default)**
- Uses **SQLite** for easy local testing.
- Flask runs in debug mode with automatic reloading.

**Production Mode**
- Uses **PostgreSQL** for database storage.
- Configured for Docker deployment with `docker-compose`.
- Flask runs with `gunicorn` for better performance.
- Cloudflare Tunnel support for exposing the app securely.

## Prerequisites

- Python 3.11+
- Flask, Flask-SQLAlchemy, Flask-WTF
- Selenium WebDriver + Google Chrome
- AWS KMS (for secure credential encryption)
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

4. **Configure environment variables**:
   Copy `.env.example` to `.env` and update:
   ```
   AWS_ACCESS_KEY_ID=<your-access-key>
   AWS_SECRET_ACCESS_KEY=<your-secret-key>
   KMS_KEY_ID=arn:aws:kms:<region>:<account-id>:key/<key-id>
   FLASK_ENV=development  # Change to production when deploying
   ```

5. **Start the Flask app (Development Mode)**:
   ```bash
   flask --app web run
   ```

6. **Run in Docker (Production Mode)**:
   ```bash
   docker compose up --build -d
   ```

   See [DEPLOY.md](DEPLOY.md) for full production deployment instructions with Cloudflare Tunnel.

## Usage

1. Open the app in your browser:
   ```
   http://127.0.0.1:5000
   ```

2. Submit your **Virginia Tech email and password**.
   - Credentials are **encrypted with AWS KMS**.
   - The app **automates Gmail login using Selenium**.
   - **Handles Duo push authentication** automatically.

3. View the **dashboard** after a successful login to see login history, adjust cadence, and check scheduler status.

## Testing

```bash
pytest
```

Runs unit and integration tests (models, KMS encryption, database operations).

## Contributing

Contributions are welcome. Feel free to fork the repository, submit pull requests, or suggest improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
