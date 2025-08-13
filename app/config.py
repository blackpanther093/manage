"""
Enhanced configuration settings for ManageIt application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class with enhanced security"""
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 14400  # 4 hours
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Database Configuration with SSL
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    
    # SSL Configuration
    DB_SSL_DISABLED = os.getenv('DB_SSL_DISABLED', 'false').lower() == 'true'
    DB_SSL_VERIFY_CERT = os.getenv('DB_SSL_VERIFY_CERT', 'true').lower() == 'true'
    
    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        raise ValueError("Database configuration incomplete")
    
    # Application Settings
    DEBUG = False
    TESTING = False
    
    # Mail Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    if not all([MAIL_USERNAME, MAIL_PASSWORD]):
        raise ValueError("Mail configuration incomplete")
    
    # LLM API Configuration    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_PLATFORM = os.getenv('GROQ_PLATFORM', 'https://api.groq.com/openai/v1/chat/completions')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Permissions-Policy': (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'fullscreen=(self), '
            'sync-xhr=()'
        ),
        "Content-Security-Policy": (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "style-src-elem 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://unpkg.com https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
            "script-src-elem 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
    }
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    WTF_CSRF_ENABLED = False  # Disable CSRF in development for easier testing

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    WTF_CSRF_ENABLED = True
    
    # Logging
    LOG_LEVEL = 'INFO'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    DB_NAME = 'test_mess_management'
    SESSION_COOKIE_SECURE = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
