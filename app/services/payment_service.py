"""
Payment-related services for ManageIt application
"""
import logging
from typing import List, Tuple
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class PaymentService:
    """Service class for payment operations"""
    
    @classmethod
    def get_payment_summary(cls, mess_name: str) -> List[Tuple]:
        """Get payment summary with caching"""
        cache_key = f"payment_summary_{mess_name}"
        
        # Try cache first
        cached_data = cache_manager.payment_cache.get(cache_key, cache_manager.PAYMENT_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            created_at = TimeUtils.get_fixed_time().date()
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT payment_date, GROUP_CONCAT(food_item SEPARATOR ', ') AS food_item, 
                           meal, SUM(amount) AS total_amount
                    FROM payment
                    WHERE mess = %s AND payment_date >= %s - INTERVAL 30 DAY
                    GROUP BY payment_date, meal
                    ORDER BY payment_date DESC
                """, (mess_name, created_at))
                data = cursor.fetchall()
                
                cache_manager.payment_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Payment summary error: {e}")
            cache_manager.payment_cache.set(cache_key, [])
            return []
    
    @classmethod
    def add_payment(cls, s_id: str, mess: str, meal: str, payment_date, 
                   food_item: str, amount: float, payment_mode: str, item_id: int) -> bool:
        """Add payment record"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    INSERT INTO payment (s_id, mess, meal, payment_date, food_item, amount, payment_mode, item_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (s_id, mess, meal, payment_date, food_item, amount, payment_mode, item_id))
                connection.commit()
                
                # Clear cache
                cls.clear_payment_cache(mess)
                return True
                
        except Exception as e:
            logging.error(f"Add payment error: {e}")
            return False
    
    @classmethod
    def get_student_payment_history(cls, student_id: str, days: int = 30) -> List[Tuple]:
        """Get student payment history"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()
                cursor.execute("""
                    SELECT mess, payment_date, meal, food_item, amount
                    FROM payment
                    WHERE payment_date >= %s - INTERVAL %s DAY
                    AND s_id = %s
                    ORDER BY payment_date DESC
                """, (created_at, days, student_id))
                return cursor.fetchall()
                
        except Exception as e:
            logging.error(f"Payment history error: {e}")
            return []
    
    @classmethod
    def clear_payment_cache(cls, mess_name: str = None):
        """Clear payment cache"""
        if mess_name:
            cache_key = f"payment_summary_{mess_name}"
            cache_manager.payment_cache.clear(cache_key)
        else:
            cache_manager.payment_cache.clear()
