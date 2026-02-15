import threading
import time
import logging
from datetime import datetime, timedelta

import schedule

from kms.kms_manager import KMSManager
from web.database import db
from web.models import EncryptedCredential
from web.services.google_login import GoogleLogin
from web.services import email_notifier
from web.services import sms_notifier

logger = logging.getLogger(__name__)

# Shared dict so the /scheduler_status endpoint can peek at what's going on
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
            if user.last_login is None:
                # first-timers haven't had a login yet, nothing to remind about
                continue

            next_login = user.last_login + timedelta(days=user.login_cadence_days)
            window_start = next_login - timedelta(days=1)

            # is next login 24-48h from now?
            if not (window_start <= now < next_login):
                continue

            # already notified for this upcoming login?
            if (
                user.last_notification_sent is not None
                and user.last_notification_sent >= window_start
            ):
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


def process_users_due_for_login(app):
    """Look at every user's cadence and log in anyone who's overdue."""
    kms_manager = KMSManager()

    with app.app_context():
        now = datetime.utcnow()
        scheduler_status["last_check"] = now.isoformat()
        scheduler_status["logins_attempted"] = 0
        scheduler_status["logins_succeeded"] = 0

        try:
            all_users = EncryptedCredential.query.all()
            scheduler_status["users_checked"] = len(all_users)

            users_due = [
                u for u in all_users
                if u.last_login is None
                or u.last_login <= now - timedelta(days=u.login_cadence_days)
            ]

            logger.info(
                "Scheduler check: %d total users, %d due for login",
                len(all_users),
                len(users_due),
            )

            if not users_due:
                scheduler_status["last_check_result"] = "No users due for login"
                return

            for user in users_due:
                scheduler_status["logins_attempted"] += 1
                try:
                    decrypted = kms_manager.decrypt(user.encrypted_key)
                    email, username, password = decrypted.split(",")

                    # text opted-in users ~1 min before we trigger the Duo push
                    if user.sms_opt_in and user.phone_number:
                        if sms_notifier.is_configured():
                            sms_notifier.send_login_sms(user.phone_number)
                            logger.info(
                                "SMS heads-up sent to %s, waiting 60s before login",
                                user.phone_number,
                            )
                            time.sleep(60)
                        else:
                            logger.debug("Twilio not configured, skipping SMS for %s", email)

                    logger.info(
                        "Attempting scheduled login for %s (cadence=%dd)",
                        email,
                        user.login_cadence_days,
                    )
                    login_bot = GoogleLogin()
                    result = login_bot.login(email, username, password)

                    if result["success"]:
                        user.last_login = datetime.utcnow()
                        db.session.commit()
                        scheduler_status["logins_succeeded"] += 1
                        logger.info("Scheduled login succeeded for %s", email)
                    else:
                        logger.warning(
                            "Scheduled login failed for %s: %s",
                            email,
                            result.get("error", "Unknown error"),
                        )
                except Exception as e:
                    logger.error("Error processing user %s: %s", user.vt_email, e)

            succeeded = scheduler_status["logins_succeeded"]
            attempted = scheduler_status["logins_attempted"]
            scheduler_status["last_check_result"] = (
                f"{succeeded}/{attempted} logins succeeded"
            )

        except Exception as e:
            scheduler_status["last_check_result"] = f"Error: {e}"
            logger.error("Scheduler check failed: %s", e)


def _daily_check(app):
    """Combined daily task: send reminders first, then do logins."""
    send_login_reminders(app)
    process_users_due_for_login(app)


def _scheduler_loop(app, interval_hours=24):
    """Runs forever in a background thread, checking on a fixed interval."""
    schedule.every(interval_hours).hours.do(_daily_check, app=app)

    def _update_next():
        next_run = schedule.next_run()
        scheduler_status["next_check"] = next_run.isoformat() if next_run else None

    _update_next()

    while True:
        schedule.run_pending()
        _update_next()
        time.sleep(60)


def start_scheduler(app, interval_hours=24):
    """Kick off the scheduler daemon thread. Called once from create_app()."""
    if scheduler_status["running"]:
        logger.warning("Scheduler already running, skipping duplicate start")
        return

    scheduler_status["running"] = True
    logger.info(
        "Starting login scheduler (interval=%dh, first run in %dh)",
        interval_hours,
        interval_hours,
    )

    thread = threading.Thread(
        target=_scheduler_loop,
        args=(app, interval_hours),
        daemon=True,
        name="login-scheduler",
    )
    thread.start()
