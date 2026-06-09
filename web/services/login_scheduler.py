import logging
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential, SchedulerState
from web.services import email_notifier, sms_notifier
from web.services.google_login import GoogleLogin

logger = logging.getLogger(__name__)

_scheduler_started = False
_succeeded_lock = threading.Lock()
_succeeded_count = 0


def next_login_time(user):
    """Next login as naive UTC, pinned to preferred_hour when set."""
    if user.last_login is None:
        return None

    anchor = user.last_login + timedelta(days=user.login_cadence_days)

    if user.preferred_hour is not None and user.timezone:
        tz = ZoneInfo(user.timezone)
        anchor_local = anchor.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        preferred = anchor_local.replace(
            hour=user.preferred_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        if preferred < anchor.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz):
            preferred += timedelta(days=1)

        # missed window? roll forward (1h grace for the hourly tick)
        now_local = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        cutoff = now_local - timedelta(hours=1)
        while preferred < cutoff:
            preferred += timedelta(days=1)

        return preferred.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    return anchor


def save_state(app, **fields):
    with app.app_context():
        state = SchedulerState.get()
        for k, v in fields.items():
            setattr(state, k, v)
        db.session.commit()


def send_login_reminders(app):
    """Email users whose next login is within 24 hours."""
    with app.app_context():
        if not email_notifier.is_configured():
            logger.debug("SMTP not configured, skipping login reminders")
            return

        now = datetime.utcnow()
        all_users = EncryptedCredential.query.all()
        sent = 0

        for user in all_users:
            if not user.email_opt_in:
                continue

            next_login = next_login_time(user)
            if next_login is None:
                continue

            window_start = next_login - timedelta(days=1)

            if not (window_start <= now < next_login):
                continue

            if user.last_notification_sent is not None and user.last_notification_sent >= window_start:
                continue

            success = email_notifier.send_login_reminder(
                to_email=user.effective_notification_email,
                next_login_utc=next_login,
                cadence_days=user.login_cadence_days,
            )
            if success:
                user.last_notification_sent = now
                db.session.commit()
                sent += 1

        save_state(app, notifications_sent=sent)
        if sent:
            logger.info("Sent %d login reminder(s)", sent)


def login_single_user(app, user_id):
    """SMS heads-up, then Selenium login for one user."""
    global _succeeded_count
    kms_manager = KMSManager()
    with app.app_context():
        user = db.session.get(EncryptedCredential, user_id)
        if not user:
            return

        email = user.vt_email
        try:
            decrypted = kms_manager.decrypt(user.encrypted_key)
            _, username, password = decrypted.split("|", maxsplit=2)

            if user.sms_opt_in and user.phone_number:
                if sms_notifier.is_configured():
                    sms_notifier.send_login_sms(user.phone_number)
                    logger.info("SMS sent to %s, waiting 60s before Duo push", user.phone_number)
                    time.sleep(60)
                else:
                    logger.debug("Twilio not configured, skipping SMS for %s", email)

            logger.info("Attempting login for %s (cadence=%dd)", email, user.login_cadence_days)
            login_bot = GoogleLogin()
            result = login_bot.login(email, username, password)

            if result["success"]:
                user.last_login = datetime.utcnow()
                db.session.commit()
                with _succeeded_lock:
                    _succeeded_count += 1
                logger.info("Login succeeded for %s", email)
            else:
                logger.warning("Login failed for %s: %s", email, result.get("error", "Unknown"))

        except Exception as e:
            logger.error("Error processing %s: %s", email, e)


def hourly_check(app):
    """Scan users, fire overdue logins, schedule ones due within the hour."""
    global _succeeded_count

    send_login_reminders(app)

    with app.app_context():
        now = datetime.utcnow()
        all_users = EncryptedCredential.query.all()

        save_state(app, last_check=now, users_checked=len(all_users), logins_attempted=0, logins_succeeded=0)

        threads = []
        overdue_count = 0
        scheduled_count = 0
        _succeeded_count = 0

        for user in all_users:
            next_login = next_login_time(user)
            if next_login is None:
                continue

            if next_login <= now:
                overdue_count += 1
                t = threading.Thread(
                    target=login_single_user,
                    args=(app, user.id),
                    name=f"login-{user.vt_email}",
                )
                t.start()
                threads.append(t)

            elif next_login <= now + timedelta(hours=1):
                delay = (next_login - now).total_seconds()
                scheduled_count += 1
                logger.info(
                    "Scheduling %s in %.0f min (at %s UTC)",
                    user.vt_email,
                    delay / 60,
                    next_login.strftime("%H:%M"),
                )
                t = threading.Timer(delay, login_single_user, args=[app, user.id])
                t.name = f"login-timer-{user.vt_email}"
                t.start()
                threads.append(t)

        attempted = overdue_count + scheduled_count

        if attempted == 0:
            save_state(app, last_result="No users due for login")
            logger.info("Hourly check: %d users, none due this window", len(all_users))
            return

        save_state(app, logins_attempted=attempted)
        logger.info(
            "Hourly check: %d users — %d overdue (now), %d scheduled (this hour)",
            len(all_users),
            overdue_count,
            scheduled_count,
        )

        for t in threads:
            t.join()

        save_state(
            app, logins_succeeded=_succeeded_count, last_result=f"{_succeeded_count}/{attempted} logins succeeded"
        )


def scheduler_loop(app):
    """Check on startup, then at the top of every hour."""
    logger.info("Running startup check for overdue logins")
    hourly_check(app)

    while True:
        now = datetime.utcnow()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait = (next_hour - now).total_seconds()
        save_state(app, next_check=next_hour)
        logger.info("Next check at %s UTC (in %.0f min)", next_hour.strftime("%H:%M"), wait / 60)
        time.sleep(wait)

        hourly_check(app)


def start_scheduler(app):
    global _scheduler_started
    if _scheduler_started:
        logger.warning("Scheduler already running, skipping duplicate start")
        return

    _scheduler_started = True
    with app.app_context():
        save_state(app, running=True)
    logger.info("Starting login scheduler (hourly checks, aligned to clock)")

    thread = threading.Thread(
        target=scheduler_loop,
        args=(app,),
        daemon=True,
        name="login-scheduler",
    )
    thread.start()
