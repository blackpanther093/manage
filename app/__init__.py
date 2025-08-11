"""
ManageIt - Mess Management System
Flask Application Factory
"""
from flask import Flask
from app.config import Config
from app.models.database import init_db_pool
from app.scheduler import start_scheduler
import os


def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.student import student_bp
    from app.blueprints.mess import mess_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(mess_bp, url_prefix='/mess')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    with app.app_context():
        init_db_pool()
    start_scheduler(app)
    return app
