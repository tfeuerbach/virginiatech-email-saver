# Virginia Tech Email Saver

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Selenium-4.27-43B02A?style=for-the-badge&logo=selenium&logoColor=white" alt="Selenium">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/AWS_KMS-Encryption-FF9900?style=for-the-badge" alt="AWS KMS">
  <img src="https://img.shields.io/badge/Gunicorn-23.0-499848?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Gunicorn">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap">
</p>

Keep your Virginia Tech Gmail account active with automated logins. This Flask-based web app securely stores your credentials, automates the entire VT SSO + Duo 2FA login flow, and lets you control how often it runs.

## Architecture

```mermaid
sequenceDiagram
    actor You
    participant App as Flask App
    participant Bot as Headless Chrome
    participant VT as VT SSO + Duo
    participant AWS as AWS KMS
    participant DB as PostgreSQL

    rect rgba(99, 0, 49, 0.08)
    Note over You,DB: First-time setup
    You->>App: Submit email + password
    App->>Bot: Verify credentials via login
    Bot->>VT: SSO → Google sign-in → Duo
    VT-->>You: 📱 Approve Duo push on phone
    Bot-->>App: Login succeeded
    App->>AWS: Encrypt credentials
    App->>DB: Store encrypted
    App-->>You: Redirected to dashboard
    end

    rect rgba(232, 119, 34, 0.08)
    Note over You,DB: Every N days (automated)
    App-->>You: 📧 Reminder email (day before)
    App-->>You: 📲 SMS reminder (~1 min before)
    App->>DB: Query accounts due for login
    App->>AWS: Decrypt credentials
    App->>Bot: Drive login flow
    Bot->>VT: SSO → Google sign-in → Duo
    VT-->>You: 📱 Approve Duo push on phone
    end
```

<details>
<summary><strong>System architecture (click to expand)</strong></summary>

```mermaid
graph TB
    subgraph Internet
        User["🌐 User"]
        CF["☁️ Cloudflare Tunnel"]
    end

    subgraph Server["Home Server · Docker Compose"]
        Gunicorn["Flask + Gunicorn<br/>Web UI · Dashboard · API"]
        Scheduler["⏰ Background Scheduler"]
        Chrome["🖥️ Headless Chrome + Selenium"]
        DB[("🗄️ PostgreSQL<br/>encrypted credentials")]
    end

    subgraph AWS["Amazon Web Services"]
        KMS["🔐 KMS<br/>encryption keys"]
        SES["📧 SES<br/>email reminders"]
    end

    subgraph Twilio["Twilio"]
        SMS["📲 SMS<br/>text reminders"]
    end

    subgraph VT["Virginia Tech"]
        SSO["SSO Portal"]
        Google["Google Sign-in"]
        Duo["Duo 2FA"]
    end

    User <-->|HTTPS| CF
    CF <-->|HTTP :5000| Gunicorn
    Gunicorn <-->|read / write| DB
    Gunicorn <-->|encrypt / decrypt| KMS

    Scheduler -->|query due accounts| DB
    Scheduler -->|decrypt credentials| KMS
    Scheduler -->|day-before reminder| SES
    Scheduler -->|1-min SMS heads-up| SMS
    Scheduler -->|automate login| Chrome

    SES -.->|📧 email| User
    SMS -.->|📲 text| User
    Chrome --> SSO --> Google --> Duo
    Duo -.->|📱 push| User
```

</details>

## Features

- **Automated Gmail Logins** — Selenium drives a headless Chrome instance through VT's SSO portal, Google sign-in, and Duo 2FA prompts.
- **Configurable Login Cadence** — Set how often the app logs in on your behalf (1–90 days, defaults to 25) via a dashboard slider.
- **Background Scheduler** — A daemon thread checks daily for accounts due for a login and runs them automatically.
- **Login Reminders** — Optional email notification the day before each login, toggleable on/off from the dashboard. Also includes a downloadable recurring `.ics` calendar event (Apple Calendar, Google Calendar, Outlook).
- **SMS Notifications** — Opt-in text message reminders via Twilio, sent ~1 minute before each scheduled login.
- **Custom Notification Email** — Use a different email address for login reminders instead of your VT email.
- **Account Removal** — Remove your account and all stored data with a swipe-to-confirm gesture. Log in again any time to re-register.
- **Privacy Policy** — In-app privacy policy covering data handling, third-party services, and opt-out instructions.
- **Dashboard** — View your last login, next scheduled login, scheduler status, and adjust all settings in one place.
- **Modern UI** — Glassmorphism cards, gradient background, Rubik font, Lottie animations, and responsive layout.
- **Production-Ready** — Gunicorn, PostgreSQL, Docker Compose, and Cloudflare Tunnel support.

## Security

Your credentials are **never stored in plaintext**. The source code is fully open — you can audit every line.

1. **AWS KMS encryption** — Credentials are encrypted with [AWS KMS](https://aws.amazon.com/kms/) before touching the database. The encryption key lives in AWS, not on the server.
2. **Session-based auth** — The dashboard is protected by server-side sessions. No user-facing URLs leak account information.
3. **CSRF protection** — Every POST endpoint is guarded by Flask-WTF CSRF tokens.
4. **Endpoint lockdown** — All sensitive endpoints require an authenticated session. Unauthenticated requests are rejected or redirected.
5. **Secure cookies** — HTTP-only, SameSite-restricted. HTTPS-only in production.
6. **No credential logging** — Passwords are never written to logs. The app uses structured Python `logging` throughout.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, Gunicorn, SQLAlchemy |
| Database | PostgreSQL (production), SQLite (development) |
| Encryption | AWS KMS via `aws-encryption-sdk` |
| Notifications | AWS SES (email), Twilio (SMS), iCalendar (.ics) |
| Browser Automation | Selenium + headless Chrome |
| Frontend | HTML/CSS/JS, Bootstrap 5, Lottie animations |
| Infrastructure | Docker Compose, Cloudflare Tunnel |

## Development vs. Production

**Development** — SQLite, Flask dev server with debug mode and auto-reload.

**Production** — PostgreSQL, Gunicorn (single worker, 4 threads), Docker Compose, optional Cloudflare Tunnel for HTTPS exposure.

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for production)
- AWS account with a KMS key
- Google Chrome (installed automatically in Docker)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tfeuerbach/virginiatech-email-saver.git
   cd virginiatech-email-saver
   ```

2. **Set up a virtual environment** (for local development):
   ```bash
   python3 -m venv .envs/vt_login
   source .envs/vt_login/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in your values:
   ```
   AWS_ACCESS_KEY_ID=<your-access-key>
   AWS_SECRET_ACCESS_KEY=<your-secret-key>
   KMS_KEY_ID=arn:aws:kms:<region>:<account-id>:key/<key-id>
   SECRET_KEY=<random-secret-for-flask-sessions>
   FLASK_ENV=development
   ```

4. **Run locally**:
   ```bash
   flask --app web run
   ```

5. **Run in Docker** (production):
   ```bash
   docker compose up --build -d
   ```

   See [DEPLOY.md](DEPLOY.md) for full production deployment instructions including Cloudflare Tunnel setup.

## Usage

1. Open `http://localhost:5000` in your browser.
2. Enter your Virginia Tech email and password. Credentials are encrypted with AWS KMS and stored securely.
3. The app automates the login flow (SSO, Google sign-in, Duo push) and redirects you to your dashboard.
4. On the dashboard you can view login history, adjust your login cadence, download a recurring calendar event, and monitor the background scheduler.
5. When a login is coming up, you'll get an email reminder (if configured) and/or a calendar alert — just approve the Duo push on your phone.

## Email Notifications

Email reminders are optional. If configured, the app emails you the day before each scheduled login so you know to have your phone ready for the Duo push.

Add these to your `.env` (works with any SMTP provider — AWS SES, Gmail app passwords, SendGrid, etc.):

```
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=VT Email Saver
SMTP_USE_TLS=true
```

If `SMTP_HOST` is blank or missing, the app still works — it just skips email reminders. The dashboard will show the feature as "Off" until configured.

You can also download a recurring `.ics` calendar event from the dashboard that adds login reminders directly to your calendar app of choice.

## Testing

```bash
# Inside Docker (recommended — has all dependencies):
docker compose exec web python -m pytest tests/ -v

# Or locally with a virtual environment:
pytest
```

Covers unit tests (models, KMS encryption, authentication, CSRF, cadence validation) and integration tests (database operations).

## Planned Improvements

- **Alembic migrations** — Replace the current `_add_column_if_missing` approach with [Alembic](https://alembic.sqlalchemy.org/) for versioned, reversible schema migrations.

## Contributing

Contributions are welcome. Feel free to fork the repository, submit pull requests, or suggest improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
