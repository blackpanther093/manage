"""
Enhanced database connection and utilities for ManageIt
"""
import mysql.connector
from mysql.connector import pooling
from flask import current_app
import logging
from contextlib import contextmanager
from app.utils.logging_config import log_security_event
import time
import os

# Configure logging
logger = logging.getLogger('database')

# Global pool variable
_connection_pool = None

def init_db_pool():
    """Initialize the MySQL connection pool with enhanced security"""
    global _connection_pool
    if _connection_pool is None:
        try:
            pool_config = {
                "pool_name": "manageit_pool",
                "pool_size": 10,  # Increased pool size
                "pool_reset_session": True,
                "host": current_app.config['DB_HOST'],
                "user": current_app.config['DB_USER'],
                "password": current_app.config['DB_PASSWORD'],
                "database": current_app.config['DB_NAME'],
                "port": current_app.config['DB_PORT'],
                "autocommit": False,
                "charset": 'utf8mb4',
                "collation": 'utf8mb4_unicode_ci',
                "time_zone": '+05:30',  # IST timezone
                "sql_mode": 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
            }
            
            ssl_ca_path = current_app.config.get('DB_SSL_CA_PATH')
            if ssl_ca_path and os.path.exists(ssl_ca_path):
                
                # If the file is found, configure and enable SSL for production (Aiven).
                logger.info("Aiven SSL is ENABLED. CA certificate found.")
                print("Aiven SSL is ENABLED. CA certificate found.")
                pool_config.update({
                    "ssl_ca": ssl_ca_path,
                    "ssl_verify_cert": True,
                    "ssl_disabled": False
                })
            else:
                # If the file is not found, disable SSL for local development.
                logger.warning("Aiven SSL is DISABLED. 'DB_SSL_CA_PATH' not set or file not found. For local dev only.")
                print("Aiven SSL is DISABLED. 'DB_SSL_CA_PATH' not set or file not found. For local dev only.")
                pool_config["ssl_disabled"] = True
            # --- END: CORRECTED SSL CONFIGURATION FOR AIVEN ---
            
            _connection_pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(" MySQL connection pool initialized with enhanced security")
            
            # Log security event
            log_security_event('database_pool_initialized', {
                'pool_size': pool_config['pool_size'],
                'ssl_enabled': not pool_config.get('ssl_disabled', True)
            })
            
        except mysql.connector.Error as e:
            logger.error(f" Error creating connection pool: {e}")
            log_security_event('database_pool_error', {'error': str(e)}, 'ERROR')
            raise

class DatabaseManager:
    """Enhanced database connection manager with security features"""
    
    @staticmethod
    def get_connection():
        """Get a pooled database connection with retry logic"""
        global _connection_pool
        if _connection_pool is None:
            init_db_pool()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = _connection_pool.get_connection()
                # Test connection
                connection.ping(reconnect=True, attempts=3, delay=1)
                return connection
            except mysql.connector.Error as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    log_security_event('database_connection_failed', {
                        'attempts': max_retries,
                        'error': str(e)
                    }, 'ERROR')
                    raise
        return None
    
    @staticmethod
    @contextmanager
    def get_db_cursor(dictionary=False):
        """Enhanced context manager for database operations with security logging"""
        connection = None
        cursor = None
        start_time = None
        
        try:
            start_time = time.time()
            
            connection = DatabaseManager.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=dictionary, buffered=True)
                yield cursor, connection
                
        except mysql.connector.Error as e:
            if connection:
                connection.rollback()
            
            # Log database errors securely
            logger.error(f"Database operation error: {e}")
            log_security_event('database_operation_error', {
                'error_code': e.errno if hasattr(e, 'errno') else 'unknown',
                'error_type': type(e).__name__
            }, 'ERROR')
            raise
            
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Unexpected database error: {e}")
            raise
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            
            # Log slow queries
            if start_time and time.time() - start_time > 1.0:
                logger.warning(f"Slow database query detected: {time.time() - start_time:.2f}s")
    
    @staticmethod
    def is_valid_student(student_id: str) -> bool:
        """Check if student ID is valid with input validation"""
        if not student_id or not isinstance(student_id, str):
            return False
        
        # Basic input validation
        if len(student_id) > 50 or not student_id.isalnum():
            log_security_event('invalid_student_id_format', {
                'student_id_hash': hash(student_id) % 10000
            }, 'WARNING')
            return False
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("SELECT s_id FROM student WHERE s_id = %s LIMIT 1", (student_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error validating student: {e}")
            return False
    
    @staticmethod
    def execute_safe_query(query: str, params: tuple = None, fetch_one: bool = False, 
                          fetch_all: bool = False, dictionary: bool = False):
        """Execute a query safely with proper error handling and logging"""
        try:
            with DatabaseManager.get_db_cursor(dictionary=dictionary) as (cursor, connection):
                cursor.execute(query, params or ())
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    connection.commit()
                    return cursor.rowcount
                    
        except mysql.connector.Error as e:
            logger.error(f"Safe query execution failed: {e}")
            log_security_event('safe_query_failed', {
                'error_code': e.errno if hasattr(e, 'errno') else 'unknown'
            }, 'ERROR')
            raise
    
    @staticmethod
    def health_check() -> dict:
        """Perform database health check"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    return {
                        'status': 'healthy',
                        'timestamp': time.time(),
                        'pool_size': _connection_pool.pool_size if _connection_pool else 0
                    }
                else:
                    return {'status': 'unhealthy', 'error': 'Invalid response'}
                    
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}

def get_db_connection():
    """Legacy function for backward compatibility"""
    return DatabaseManager.get_connection()
