import logging
import threading
import time
from datetime import datetime, timedelta

from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential
from web.services import email_notifier, sms_notifier
from web.services.google_login import GoogleLogin

logger = logging.getLogger(__name__)

scheduler_status = {
    "running": False,
    "last_check": None,
    "last_check_result": None,
    "users_checked": 0,
    "logins_attempted": 0,
    "logins_succeeded": 0,
    "notifications_sent": 0,
    "sms_sent": 0,
    "next_check": None,
}


def _next_login_time(user):
    """Compute when a user's next login should happen based on DB state."""
    if user.last_login is None:
        return None
    return user.last_login + timedelta(days=user.login_cadence_days)


def send_login_reminders(app):
    """Email users whose next login is within the next 24-48 hours."""
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

            next_login = _next_login_time(user)
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

        scheduler_status["notifications_sent"] = sent
        if sent:
            logger.info("Sent %d login reminder(s)", sent)


def _login_single_user(app, user_id):
    """Run one user's login flow in its own thread (SMS → wait → Selenium)."""
    kms_manager = KMSManager()
    with app.app_context():
        user = db.session.get(EncryptedCredential, user_id)
        if not user:
            return

        email = user.vt_email
        try:
            decrypted = kms_manager.decrypt(user.encrypted_key)
            _, username, password = decrypted.split(",")

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
                scheduler_status["logins_succeeded"] += 1
                logger.info("Login succeeded for %s", email)
            else:
                logger.warning("Login failed for %s: %s", email, result.get("error", "Unknown"))

        except Exception as e:
            logger.error("Error processing %s: %s", email, e)


def _hourly_check(app):
    """Scan all users at the top of each hour.

    - Overdue (next_login in the past): login immediately
    - Due within 60 min: start a timer that fires at the exact minute
    - Due later: do nothing, we'll catch them on a future check

    All timers run concurrently; the function blocks until every login
    in this window has finished before returning to the sleep loop.
    """
    send_login_reminders(app)

    with app.app_context():
        now = datetime.utcnow()
        scheduler_status["last_check"] = now.isoformat()
        scheduler_status["logins_attempted"] = 0
        scheduler_status["logins_succeeded"] = 0

        all_users = EncryptedCredential.query.all()
        scheduler_status["users_checked"] = len(all_users)

        threads = []
        overdue_count = 0
        scheduled_count = 0

        for user in all_users:
            next_login = _next_login_time(user)
            if next_login is None:
                continue

            if next_login <= now:
                # overdue — fire immediately
                scheduler_status["logins_attempted"] += 1
                overdue_count += 1
                t = threading.Thread(
                    target=_login_single_user,
                    args=(app, user.id),
                    name=f"login-{user.vt_email}",
                )
                t.start()
                threads.append(t)

            elif next_login <= now + timedelta(hours=1):
                # due within the hour — set a countdown timer
                delay = (next_login - now).total_seconds()
                scheduler_status["logins_attempted"] += 1
                scheduled_count += 1
                logger.info(
                    "Scheduling %s in %.0f min (at %s UTC)",
                    user.vt_email,
                    delay / 60,
                    next_login.strftime("%H:%M"),
                )
                t = threading.Timer(delay, _login_single_user, args=[app, user.id])
                t.name = f"login-timer-{user.vt_email}"
                t.start()
                threads.append(t)

        total = overdue_count + scheduled_count
        if total == 0:
            scheduler_status["last_check_result"] = "No users due for login"
            logger.info("Hourly check: %d users, none due this window", len(all_users))
            return

        logger.info(
            "Hourly check: %d users — %d overdue (now), %d scheduled (this hour)",
            len(all_users),
            overdue_count,
            scheduled_count,
        )

        for t in threads:
            t.join()

        succeeded = scheduler_status["logins_succeeded"]
        attempted = scheduler_status["logins_attempted"]
        scheduler_status["last_check_result"] = f"{succeeded}/{attempted} logins succeeded"


def scheduler_loop(app):
    """Run forever: check on startup, then again at the top of every hour."""

    logger.info("Running startup check for overdue logins")
    _hourly_check(app)

    while True:
        now = datetime.utcnow()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait = (next_hour - now).total_seconds()
        scheduler_status["next_check"] = next_hour.isoformat()
        logger.info("Next check at %s UTC (in %.0f min)", next_hour.strftime("%H:%M"), wait / 60)
        time.sleep(wait)

        _hourly_check(app)


def start_scheduler(app):
    """Kick off the scheduler daemon thread. Called once from create_app()."""
    if scheduler_status["running"]:
        logger.warning("Scheduler already running, skipping duplicate start")
        return

    scheduler_status["running"] = True
    logger.info("Starting login scheduler (hourly checks, aligned to clock)")

    thread = threading.Thread(
        target=scheduler_loop,
        args=(app,),
        daemon=True,
        name="login-scheduler",
    )
    thread.start()
