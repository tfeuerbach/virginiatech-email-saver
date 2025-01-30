from flask import Flask
from web.routes.form_routes import form_bp
from web.routes.dashboard_routes import dashboard_bp
from web.routes.progress_routes import progress_bp
from web.routes.schedule_routes import schedule_bp
from web.routes.processing_routes import processing_bp 

def register_routes(app: Flask):
    """Register all Flask blueprints (routes)"""
    app.register_blueprint(form_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(processing_bp)
