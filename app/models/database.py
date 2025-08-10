"""
Database connection and utilities for ManageIt
"""
import mysql.connector
from flask import current_app
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager"""
    
    @staticmethod
    def get_connection():
        """Get database connection with error handling"""
        try:
            connection = mysql.connector.connect(
                host=current_app.config['DB_HOST'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                database=current_app.config['DB_NAME'],
                port=current_app.config['DB_PORT'],
                autocommit=False
            )
            return connection
        except mysql.connector.Error as e:
            logging.error(f"Database connection error: {e}")
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
            logging.error(f"Database operation error: {e}")
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
            logging.error(f"Error validating student: {e}")
            return False

def get_db_connection():
    """Legacy function for backward compatibility"""
    return DatabaseManager.get_connection()
