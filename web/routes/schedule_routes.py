from flask import Blueprint, current_app, jsonify, session

from web.services.login_scheduler import (
    process_users_due_for_login,
    scheduler_status,
)

schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/schedule_logins", methods=["POST"])
def schedule_logins():
    """Manually kick off a login check — requires an active session."""
    if not session.get("authenticated_email"):
        return jsonify({"error": "Not authenticated"}), 401

    try:
        process_users_due_for_login(current_app._get_current_object())
        return jsonify(
            {
                "message": "Login check completed.",
                "status": scheduler_status,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to run login check: {e}"}), 500


@schedule_bp.route("/scheduler_status", methods=["GET"])
def get_scheduler_status():
    """Quick peek at whether the scheduler is alive and what it's up to."""
    if not session.get("authenticated_email"):
        return jsonify({"error": "Not authenticated"}), 401

    return jsonify(scheduler_status)
