from flask import Blueprint, render_template

processing_bp = Blueprint("processing", __name__)

@processing_bp.route("/processing", methods=["GET"])
def processing():
    """Show the processing/animation page while login runs."""
    return render_template("submit.html")
