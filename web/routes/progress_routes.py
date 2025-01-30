from flask import Blueprint, request, jsonify, current_app

progress_bp = Blueprint("progress", __name__)

def get_progress_store():
    """Ensure progress tracking is consistent across all modules."""
    if not hasattr(current_app, "progress_updates"):
        current_app.progress_updates = {"step": 0, "error": ""}
    return current_app.progress_updates

@progress_bp.route("/update_progress", methods=["POST"])
def update_progress():
    """Update the login progress step."""
    progress_updates = get_progress_store()
    step = request.json.get("step", 0)
    
    if step > progress_updates["step"]:
        progress_updates["step"] = step

    print(f"Progress updated to step: {progress_updates['step']}")  # Ensure this prints
    return jsonify({"status": "updated", "current_step": progress_updates["step"]})

@progress_bp.route("/get_progress", methods=["GET"])
def get_progress():
    """Retrieve the current login progress."""
    progress_updates = get_progress_store()
    print(f"Current progress: {progress_updates}")  # Ensure this prints
    return jsonify(progress_updates)
