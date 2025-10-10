"""
ManageIt - Mess Management System
Flask Application Factory
"""
import os
import logging
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, request, session
from flask_compress import Compress
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman

from app.config import Config, config
from app.models.database import init_db_pool, DatabaseManager
from app.scheduler import start_scheduler
from app.utils.logging_config import setup_logging, log_security_event
from app.utils.security import security_manager
from app.utils.validators import InputValidator

compress = Compress()
# org_name = 'iiitdmk'

def create_app(config_name=None):
    """Create and configure Flask application"""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Determine config
    if not config_name:
        config_name = os.getenv('FLASK_CONFIG', os.getenv('FLASK_ENV', 'production'))
    cfg_class = config.get(config_name, Config)
    app.config.from_object(cfg_class)

    # Only initialize compression if COMPRESS_ALGORITHM is set
    if app.config.get('COMPRESS_ALGORITHM'):
        compress.init_app(app)
    # Compression
    # Compress(app)

    # CORS
    if config_name == 'production':
        CORS(app,
             origins=['https://manage-lths.onrender.com/'],
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             supports_credentials=True)
    else:
        CORS(app)

    # Logging
    if config_name == 'production':
        setup_production_logging(app)
    else:
        setup_logging(app)

    # CSRF
    if app.config.get('WTF_CSRF_ENABLED', False):
        CSRFProtect(app)

    # Rate limiter (device-based)
    def get_device_key():
        ip = security_manager.get_client_ip()
        device_id = security_manager.get_device_fingerprint()
        user_id = session.get('user_id', 'anonymous')
        return f"{user_id}:{ip}:{device_id}"

    Limiter(
        app=app,
        key_func=get_device_key,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', "200 per day, 50 per hour")],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    )

    # Talisman
    if config_name == 'production':
        csp = app.config.get('SECURITY_HEADERS', {}).get('Content-Security-Policy')
        Talisman(app,
                force_https=True,
                strict_transport_security=True,
                content_security_policy=csp)

    # Cache headers
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)

    @app.after_request
    def add_cache_headers(response):
        if response.status_code == 200 and 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'public, max-age=7200'
        return response

    # Security hooks
    @app.before_request
    def security_before_request():
        if request.endpoint == 'health_check':
            return
        identifier = session.get('user_id', '')
        if security_manager.is_device_blocked(identifier):
            log_security_event('blocked_device_access_attempt', {
                'ip': security_manager.get_client_ip(),
                'device_id': security_manager.get_device_fingerprint()[:8]
            }, 'WARNING')
            return "Access denied", 403
        if 'role' in session and not security_manager.validate_session():
            session.clear()
            return "Session expired", 401

    @app.after_request
    def security_after_request(response):
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        if config_name == 'production':
            response.headers['Access-Control-Allow-Origin'] = 'https://manage-lths.onrender.com'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        return response

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"Bad request from {request.remote_addr}: {error}")
        return "Bad Request", 400

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"Forbidden access from {request.remote_addr}: {error}")
        return "Forbidden", 403

    @app.errorhandler(404)
    def not_found(error):
        return "Page Not Found", 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"Rate limit exceeded from {request.remote_addr}")
        return "Rate limit exceeded", 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return "Internal Server Error", 500

    # Health check
    @app.route('/health')
    def health_check():
        if config_name == 'production':
            token = request.args.get('token', '')
            if token != app.config.get('HEALTH_TOKEN'):
                return "Unauthorized", 401
        try:
            db_health = DatabaseManager.health_check()
            status_code = 200 if db_health['status'] == 'healthy' else 503
            return {
                'status': 'healthy' if status_code == 200 else 'unhealthy',
                'timestamp': os.times(),
                'database': db_health,
                'version': '1.0.0'
            }, status_code
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 503


    # Security status
    @app.route('/security/status')
    def security_status():
        if session.get('role') != 'admin':
            return "Unauthorized", 401
        return security_manager.get_security_stats()

    # Template filters
    @app.template_filter('sanitize')
    def sanitize_filter(text):
        return InputValidator.sanitize_html(str(text))

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
    # app.register_blueprint(main_bp, url_prefix='/<org_name>')
    # app.register_blueprint(auth_bp, url_prefix='/<org_name>/auth')
    # app.register_blueprint(student_bp, url_prefix='/<org_name>/student')
    # app.register_blueprint(mess_bp, url_prefix='/<org_name>/mess')
    # app.register_blueprint(admin_bp, url_prefix='/<org_name>/admin')

    # DB init
    with app.app_context():
        init_db_pool()

    # Scheduler
    try:
        start_scheduler(app)
        app.logger.info("Scheduler started successfully.")
    except Exception as e:
        app.logger.error(f"Error starting scheduler: {e}")
        raise

    app.logger.info(f"Flask application created with {config_name} configuration")
    return app

def setup_production_logging(app):
    if not app.debug and not app.testing:
        log_dir = os.path.dirname(app.config.get('LOG_FILE', '/var/log/manageit/app.log'))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', '/var/log/manageit/app.log'),
            maxBytes=app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024),
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('ManageIt startup - Production mode')
