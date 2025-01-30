from flask import Blueprint, jsonify
from web.services.login_scheduler import VTLoginScheduler

schedule_bp = Blueprint("schedule", __name__)

login_scheduler = VTLoginScheduler()

@schedule_bp.route("/schedule_logins", methods=["POST"])
def schedule_logins():
    """Manually trigger login scheduling."""
    try:
        login_scheduler.schedule_users()
        return jsonify({"message": "Scheduled logins successfully!"})
    except Exception as e:
        return jsonify({"error": "Failed to schedule logins."}), 500