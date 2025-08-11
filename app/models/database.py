"""
Database connection and utilities for ManageIt
"""
import mysql.connector
from mysql.connector import pooling
from flask import current_app
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global pool variable
_connection_pool = None

def init_db_pool():
    """Initialize the MySQL connection pool (call this once on app startup)"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pooling.MySQLConnectionPool(
                pool_name="manageit_pool",
                pool_size=5,  # adjust depending on concurrency
                host=current_app.config['DB_HOST'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                database=current_app.config['DB_NAME'],
                port=current_app.config['DB_PORT'],
                autocommit=False
            )
            logger.info("✅ MySQL connection pool initialized")
        except mysql.connector.Error as e:
            logger.error(f"❌ Error creating connection pool: {e}")
            raise

class DatabaseManager:
    """Database connection manager with pooling"""
    
    @staticmethod
    def get_connection():
        """Get a pooled database connection"""
        global _connection_pool
        if _connection_pool is None:
            init_db_pool()
        try:
            return _connection_pool.get_connection()
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    @staticmethod
    @contextmanager
    def get_db_cursor(dictionary=False):
        """Context manager for database operations"""
        connection = None
        cursor = None
        try:
            connection = DatabaseManager.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=dictionary)
                yield cursor, connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database operation error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    @staticmethod
    def is_valid_student(student_id):
        """Check if student ID is valid"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("SELECT s_id FROM student WHERE s_id = %s", (student_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error validating student: {e}")
            return False

def get_db_connection():
    """Legacy function for backward compatibility"""
    return DatabaseManager.get_connection()
