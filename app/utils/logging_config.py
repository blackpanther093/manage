"""
Logging configuration for ManageIt application
"""
import logging
import logging.handlers
import os
from datetime import datetime
import json

class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_FIELDS = ['password', 'token', 'api_key', 'secret', 'csrf_token']
    
    def filter(self, record):
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            for field in self.SENSITIVE_FIELDS:
                if field in msg.lower():
                    # Replace sensitive data with placeholder
                    record.msg = msg.replace(field, f"{field}=***REDACTED***")
        return True

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging(app):
    """Setup comprehensive logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Set logging level
    app.logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    )
    
    json_formatter = JSONFormatter()
    
    # Application log handler (rotating)
    app_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    app_handler.addFilter(SecurityFilter())
    
    # Security log handler
    security_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'security.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(json_formatter)
    
    # Error log handler
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler for development
    if app.config.get('DEBUG'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(detailed_formatter)
        app.logger.addHandler(console_handler)
    
    # Add handlers to app logger
    app.logger.addHandler(app_handler)
    app.logger.addHandler(security_handler)
    app.logger.addHandler(error_handler)
    
    # Setup security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_handler)
    
    # Setup database logger
    db_logger = logging.getLogger('database')
    db_logger.setLevel(logging.INFO)
    db_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'database.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    db_handler.setFormatter(detailed_formatter)
    db_logger.addHandler(db_handler)
    
    app.logger.info("Logging configuration completed")

def log_security_event(event_type: str, details: dict, level: str = 'INFO'):
    """Log security events"""
    security_logger = logging.getLogger('security')
    
    log_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        **details
    }
    
    if level.upper() == 'WARNING':
        security_logger.warning(json.dumps(log_data))
    elif level.upper() == 'ERROR':
        security_logger.error(json.dumps(log_data))
    else:
        security_logger.info(json.dumps(log_data))
