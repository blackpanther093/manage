"""
Enhanced Flask application factory with comprehensive security
"""
import os
import sys
import time
import base64
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, session, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman

from app import create_app
from app.config import config
from app.models.database import init_db_pool, DatabaseManager
from app.utils.logging_config import setup_logging, log_security_event
from app.utils.security import security_manager
from app.utils.validators import InputValidator, ValidationError

# Import blueprints
from app.blueprints.main import main_bp
from app.blueprints.auth import auth_bp
from app.blueprints.student import student_bp
from app.blueprints.mess import mess_bp
from app.blueprints.admin import admin_bp


def create_app(config_name='default'):
    """Create Flask application with enhanced security"""
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup production logging
    if config_name == 'production':
        setup_production_logging(app)
    else:
        setup_logging(app)
    
    # Initialize security extensions
    csrf = CSRFProtect(app)
    
    # Initialize rate limiter with Redis for production
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', "200 per day, 50 per hour")],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    )
    
    # Security headers with Talisman
    Talisman(app, 
             force_https=(config_name == 'production'),  # Force HTTPS in production
             strict_transport_security=True,
             permissions_policy={},  # Disable automatic permissions policy
             content_security_policy=False)  # We'll handle CSP manually
    
    # Initialize database pool
    with app.app_context():
        init_db_pool()

    # Security middleware
    @app.before_request
    def security_before_request():
        """Security checks before each request"""
        # Check if IP is blocked
        client_ip = security_manager.get_client_ip()
        if security_manager.is_ip_blocked(client_ip):
            log_security_event('blocked_ip_access_attempt', {'ip': client_ip}, 'WARNING')
            return "Access denied", 403
        
        # Validate session
        if 'role' in session:
            if not security_manager.validate_session():
                session.clear()
                return "Session expired", 401
        
        # Log security-relevant requests
        if request.endpoint in ['auth.login', 'auth.signup', 'admin.dashboard']:
            log_security_event('security_endpoint_access', {
                'endpoint': request.endpoint,
                'ip': client_ip,
                'user_agent': request.headers.get('User-Agent', '')[:100]
            })

    @app.after_request
    def security_after_request(response):
        """Apply security headers after each request"""
        # Add all security headers from config
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        
        # Log failed requests in production
        if response.status_code >= 400 and config_name == 'production':
            log_security_event('failed_request', {
                'status_code': response.status_code,
                'endpoint': request.endpoint,
                'ip': security_manager.get_client_ip()
            }, 'WARNING' if response.status_code >= 500 else 'INFO')
        
        return response

    
    # Error handlers with security logging
    @app.errorhandler(400)
    def bad_request(error):
        log_security_event('bad_request', {
            'ip': security_manager.get_client_ip(),
            'endpoint': request.endpoint
        }, 'WARNING')
        return "Bad Request", 400
    
    @app.errorhandler(403)
    def forbidden(error):
        log_security_event('forbidden_access', {
            'ip': security_manager.get_client_ip(),
            'endpoint': request.endpoint
        }, 'WARNING')
        return "Forbidden", 403
    
    @app.errorhandler(404)
    def not_found(error):
        return "Page Not Found", 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        log_security_event('rate_limit_exceeded', {
            'ip': security_manager.get_client_ip(),
            'endpoint': request.endpoint,
            'limit': str(e.description)
        }, 'WARNING')
        return "Rate limit exceeded", 429
    
    @app.errorhandler(500)
    def internal_error(error):
        log_security_event('internal_server_error', {
            'ip': security_manager.get_client_ip(),
            'endpoint': request.endpoint
        }, 'ERROR')
        return "Internal Server Error", 500
    
    # Health check endpoint
    @app.route('/health')
    @limiter.limit("10 per minute")
    def health_check():
        """Application health check"""
        db_health = DatabaseManager.health_check()
        
        health_status = {
            'status': 'healthy' if db_health['status'] == 'healthy' else 'unhealthy',
            'timestamp': time.time(),
            'database': db_health,
            'version': '1.0.0'
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return health_status, status_code
    
    # Security endpoint for monitoring
    @app.route('/security/status')
    @limiter.limit("5 per minute")
    def security_status():
        """Security status endpoint (admin only)"""
        if session.get('role') != 'admin':
            return "Unauthorized", 401
        
        return {
            'blocked_ips': len(security_manager.blocked_ips),
            'failed_attempts': len(security_manager.failed_attempts),
            'email_rate_limits': len(security_manager.email_attempts)
        }
    
    # Apply rate limiting to authentication endpoints
    limiter.limit("5 per minute")(auth_bp)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(mess_bp, url_prefix='/mess')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Custom template filters for security
    @app.template_filter('sanitize')
    def sanitize_filter(text):
        """Template filter to sanitize HTML"""
        return InputValidator.sanitize_html(str(text))
    
    app.logger.info(f"Flask application created with {config_name} configuration")
    
    return app


def setup_production_logging(app):
    """Setup production logging with file rotation"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(app.config.get('LOG_FILE', '/var/log/manageit/app.log'))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Setup rotating file handler
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


if __name__ == '__main__':
    # Get environment from environment variable
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    
    if env == 'production':
        # Production should use a proper WSGI server like Gunicorn
        print("WARNING: Use a production WSGI server like Gunicorn for production deployment")
        print("Example: gunicorn -w 4 -b 0.0.0.0:8000 'run:create_app(\"production\")'")
        sys.exit(1)
    else:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=app.config.get('DEBUG', False)
        )
