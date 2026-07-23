# VT Email Saver — Deployment Context Sheet

Use this document to onboard a new agent or resume work on a new server. It covers everything needed to deploy via Docker + Cloudflare Tunnel.

## What This App Does

Flask web app that stores Virginia Tech Gmail credentials (encrypted with AWS KMS), then uses Selenium + Chrome to automatically log in on a schedule so the VT email account stays active. Users set a cadence (e.g. every 25 days), pick a preferred time of day, and approve Duo 2FA pushes when prompted.

## Architecture

Single-process Flask monolith. No Celery, no Redis, no task queue.

- **Web server:** Gunicorn, 1 worker, 4 threads (single process required for in-memory state)
- **Background scheduler:** Python `threading.Thread` daemon, clock-aligned hourly checks
- **Database:** PostgreSQL 15 in Docker (SQLite fallback for local dev)
- **Credential encryption:** AWS KMS encrypt/decrypt, stored as `email|username|password` (pipe-delimited) base64 blob
- **Login automation:** Selenium + headless Chrome inside the Docker container
- **Notifications:** Optional SMTP email reminders (24h before login) and Twilio SMS (1 min before Duo push)
- **Public access:** Cloudflare Tunnel (no inbound ports needed on the server)

## Tech Stack

- Python 3.11, Flask 3.1, SQLAlchemy 2.0, Gunicorn
- PostgreSQL 15 (Docker)
- Selenium 4.27 + Chrome (installed in Dockerfile)
- AWS KMS (boto3) for credential encryption
- Docker + Docker Compose
- Cloudflare Tunnel (`cloudflared`) for HTTPS
- Ruff for linting/formatting, pytest for tests
- GitHub Actions CI (ruff + pytest)

## Directory Structure

```
├── Dockerfile              # Python 3.11 + Chrome + Gunicorn
├── docker-compose.yml      # web + db + optional tunnel
├── requirements.txt        # Pinned Python deps
├── pyproject.toml          # Ruff + pytest config
├── .env.example            # Template for all env vars
├── .github/workflows/ci.yml
├── kms/
│   └── kms_manager.py      # AWS KMS encrypt/decrypt wrapper
├── web/
│   ├── __init__.py          # create_app() factory, DB init, scheduler start
│   ├── config.py            # Dev/Prod config from .env
│   ├── models.py            # EncryptedCredential, SchedulerState
│   ├── routes/
│   │   ├── dashboard_routes.py   # Settings, timezone, cadence, SMS, calendar
│   │   ├── form_routes.py        # Login form + credential submission
│   │   ├── schedule_routes.py    # Manual scheduler trigger + status
│   │   ├── progress_routes.py    # Login progress polling
│   │   └── processing_routes.py  # Processing page
│   ├── services/
│   │   ├── login_scheduler.py    # Threading-based hourly scheduler
│   │   ├── google_login.py       # Selenium Chrome automation
│   │   ├── email_notifier.py     # SMTP emails
│   │   └── sms_notifier.py       # Twilio SMS
│   ├── static/                   # CSS, JS, animations, images
│   └── templates/                # Jinja2 HTML templates
└── tests/                        # 110 tests, ~1s runtime
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Here's what matters:

### Required

| Variable | What |
|----------|------|
| `AWS_ACCESS_KEY_ID` | IAM user with `kms:Encrypt` + `kms:Decrypt` |
| `AWS_SECRET_ACCESS_KEY` | IAM secret |
| `KMS_KEY_ID` | KMS key ARN |
| `SECRET_KEY` | Flask session secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `POSTGRES_USER` | Postgres username |
| `POSTGRES_PASSWORD` | Postgres password |
| `POSTGRES_DB` | Database name |
| `DATABASE_URL` | `postgresql://user:pass@db:5432/dbname` |
| `FLASK_ENV` | `production` for deployment |

### Optional

| Variable | What | Default |
|----------|------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `SMTP_HOST` | SMTP server (blank = no emails) | disabled |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP auth | blank |
| `SMTP_FROM_EMAIL` | Sender address | `noreply@vtemailsaver.tfeuerbach.dev` |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | SMS (blank = disabled) | disabled |
| `CLOUDFLARE_TUNNEL_TOKEN` | Tunnel token from Cloudflare Zero Trust dashboard | n/a |
| `BASE_URL` | Public URL for email links | `https://vtemailsaver.tfeuerbach.dev` |
| `INTERNAL_URL` | Selenium -> Flask callback URL | `http://127.0.0.1:5000` |

## Deploy Commands

```bash
# Clone and configure
git clone <repo-url> && cd virginiatech-email-saver
cp .env.example .env
# Edit .env with real values

# Build and start (without Cloudflare Tunnel)
docker compose up --build -d

# Build and start (with Cloudflare Tunnel)
docker compose --profile tunnel up --build -d

# Check logs
docker compose logs -f web
docker compose logs -f tunnel

# Backup database
docker exec postgres_db pg_dump -U postgres encrypted_credentials > backup.sql
```

## Ports

| Port | Service | Exposed? |
|------|---------|----------|
| 5000 | Gunicorn/Flask | Published `5000:5000` in docker-compose |
| 5432 | PostgreSQL | Internal Docker network only |
| 9222 | Chrome debug | Internal to web container |

With Cloudflare Tunnel, port 5000 does not need to be publicly accessible. The tunnel connects to `http://web:5000` inside the Docker network.

## Scheduler Details

- Starts automatically when `create_app()` runs (skipped when `TESTING=1`)
- Single daemon thread, clock-aligned to run at the top of every hour (UTC)
- Each hourly check: sends email reminders, then scans all users for overdue/upcoming logins
- Overdue logins fire immediately in parallel threads
- Logins due within the hour get a `threading.Timer` for precise scheduling
- Users with `preferred_hour` + `timezone` set get their login pinned to that local time
- 1-hour grace window prevents overdue logins from firing at wrong times after restarts
- State tracked in `SchedulerState` DB row (viewable at `/scheduler_status`)

## Gunicorn Config (from Dockerfile)

```
gunicorn web:create_app()
  --bind 0.0.0.0:5000
  --workers 1          # MUST be 1 — scheduler + in-memory progress state
  --threads 4
  --timeout 300        # Selenium logins can be slow
  --preload
```

Do not increase workers above 1 — the scheduler uses a module-level `_scheduler_started` guard and in-memory `progress_updates` dict that don't work across processes.

## Running Tests Locally

```bash
# Create venv with Python 3.11 (matches CI + Docker)
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run tests
.venv/bin/pytest tests/ -v

# Run linter
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Tests use in-memory SQLite, no external services needed. 110 tests, runs in ~1 second.

## CI Pipeline

GitHub Actions (`.github/workflows/ci.yml`):
1. **Lint job:** Ruff check + format check (Python 3.11)
2. **Test job:** `pip install -r requirements.txt` then `pytest tests/ -v` with mock AWS env vars

## Pre-commit Hook

A git pre-commit hook at `.git/hooks/pre-commit` runs `ruff check` and `ruff format --check` before every commit. It uses `.venv/bin/ruff` if available.

## Credential Storage Format

Credentials are stored as: `email|username|password` (pipe-delimited), encrypted with AWS KMS, base64-encoded, in the `encrypted_key` column of `EncryptedCredential`.

The pipe delimiter was chosen because passwords can contain commas but are unlikely to contain pipes. `maxsplit=2` is used on decrypt so even a pipe in the password wouldn't break parsing.

## Database Migrations

No Alembic. New columns are added via `add_column_if_missing()` in `web/__init__.py` which checks `information_schema` and runs `ALTER TABLE` if needed. Only runs on PostgreSQL (skipped for SQLite).

## Cloudflare Tunnel Setup

1. Create a tunnel in the Cloudflare Zero Trust dashboard
2. Point it to `http://web:5000`
3. Set the `CLOUDFLARE_TUNNEL_TOKEN` in `.env`
4. Run with `docker compose --profile tunnel up --build -d`

The tunnel service is gated behind a Docker Compose profile so it doesn't start unless explicitly requested.

## Known Constraints

- **Single Gunicorn worker required** — scheduler and progress tracking use in-memory state
- **Server operator can decrypt credentials** — inherent to the design (app needs plaintext to perform logins)
- **Chrome/Selenium inside Docker** — the Dockerfile installs Chrome stable + matching ChromeDriver
- **Duo 2FA requires user's phone** — the scheduler sends SMS 60s before Duo push if Twilio is configured
- **No Alembic** — schema changes are handled by `add_column_if_missing()` at startup
