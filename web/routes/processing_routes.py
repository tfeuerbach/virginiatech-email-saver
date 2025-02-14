from flask import Blueprint, render_template

processing_bp = Blueprint("processing", __name__)

@processing_bp.route("/processing", methods=["GET"])
def processing():
    """Render the processing page (submit.html)."""
    return render_template("submit.html")