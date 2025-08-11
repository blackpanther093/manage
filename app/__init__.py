"""
ManageIt - Mess Management System
Flask Application Factory
"""
from flask import Flask
from flask_compress import Compress
from app.config import Config
from app.models.database import init_db_pool
from app.scheduler import start_scheduler
import os
from datetime import timedelta


def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    Compress(app)
    app.config.from_object(config_class)
    
    # Set cache timeout for static files to 1 day (adjust as needed)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)

    @app.after_request
    def add_cache_headers(response):
        # Cache all GET responses for 1 day
        if response.status_code == 200 and 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

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
