from flask import Blueprint, redirect, render_template, session, url_for

processing_bp = Blueprint("processing", __name__)


@processing_bp.route("/processing", methods=["GET"])
def processing():
    """Show the processing/animation page while login runs."""
    if not session.get("authenticated_email"):
        return redirect(url_for("form.index"))
    return render_template("submit.html")
