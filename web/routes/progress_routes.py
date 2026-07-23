import logging

from flask import Blueprint, current_app, jsonify, request, session

from web.csrf import csrf

logger = logging.getLogger(__name__)

progress_bp = Blueprint("progress", __name__)


def get_progress_store():
    """Get the shared progress dict (lives on the app object)."""
    if not hasattr(current_app, "progress_updates"):
        current_app.progress_updates = {"step": 0, "error": "", "duo_code": ""}
    return current_app.progress_updates


@progress_bp.route("/update_progress", methods=["POST"])
@csrf.exempt
def update_progress():
    """Bump the progress step (only moves forward, never backward).

    Exempt from CSRF — called server-to-server by google_login.py.
    """
    progress_updates = get_progress_store()
    data = request.json or {}
    step = data.get("step", 0)
    duo_code = data.get("duo_code")

    if step > progress_updates["step"]:
        progress_updates["step"] = step

    if duo_code is not None:
        progress_updates["duo_code"] = duo_code

    logger.debug("Progress updated to step: %s", progress_updates["step"])
    return jsonify({"status": "updated", "current_step": progress_updates["step"]})


@progress_bp.route("/get_progress", methods=["GET"])
def get_progress():
    """Return current login progress for the polling frontend."""
    if not session.get("authenticated_email"):
        return jsonify({"error": "Not authenticated"}), 401

    progress_updates = get_progress_store()
    logger.debug("Current progress: %s", progress_updates)
    return jsonify(progress_updates)
