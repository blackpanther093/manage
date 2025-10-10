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
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 14400  # 4 hours
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True # Disable CSRF for now to fix login issues
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
    BREVO_API_KEY = os.getenv('BREVO_API_KEY')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')
       
    # LLM API Configuration    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_PLATFORM = os.getenv('GROQ_PLATFORM', 'https://api.groq.com/openai/v1/chat/completions')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    # Rate Limiting - Production Redis
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
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
    
    # Logging Configuration
    LOG_LEVEL = 'INFO'
    # LOG_FILE = os.getenv('LOG_FILE', '/var/log/manageit/app.log')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    COMPRESS_ALGORITHM = None
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    # WTF_CSRF_ENABLED = False  # Disable CSRF in development for easier testing
    WTF_CSRF_ENABLED = True  # Disable CSRF in development for easier testing
    RATELIMIT_STORAGE_URL = 'memory://'  # Use memory for development
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration with enhanced security"""

    HEALTH_TOKEN = os.getenv('HEALTH_TOKEN', 'your_default_secure_token_here')

    DEBUG = False
    TESTING = False
    
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'  # Default to false for Render
    SESSION_COOKIE_HTTPONLY = True
    # WTF_CSRF_ENABLED = False  # Disable CSRF temporarily to fix login
    WTF_CSRF_ENABLED = True  # Disable CSRF temporarily to fix login
    
    PREFERRED_URL_SCHEME = 'https'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    COMPRESS_ALGORITHM = 'gzip'
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500

    RATELIMIT_DEFAULT = "500 per day, 100 per hour"  # More lenient limits
    
    # Production database with connection pooling
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
    
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        # In your ProductionConfig class in config.py

        "Content-Security-Policy": (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src-elem 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            
            # ADDED 'data:' to allow embedded fonts from CSS files
            "font-src 'self' data: https://unpkg.com https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "script-src-elem 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: blob:; "

            # ADDED the CDN to allow developer source maps to be fetched
            "connect-src 'self' https://cdn.jsdelivr.net https:; "
            
            "object-src 'none'; "
            "base-uri 'self';"
        )
    }

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    DB_NAME = 'test_mess_management'
    SESSION_COOKIE_SECURE = False
    RATELIMIT_STORAGE_URL = 'memory://'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
