"""
Waste-related services for ManageIt application
"""
import logging
from typing import List, Tuple, Dict, Any
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class WasteService:
    """Service class for waste operations"""
    
    CACHE_TTL = 86400  # 24 hours
    
    @classmethod
    def get_waste_feedback(cls, mess_name: str) -> Tuple[List[Dict], List[Dict]]:
        """Fetch waste + feedback analysis for a mess with caching"""
        cache_key = f"waste_feedback_{mess_name}"
        cache = cache_manager.get_cache('waste_feedback')
        cached_data = cache.get(cache_key, cls.CACHE_TTL)
        
        if cached_data is not None:
            return cached_data

        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()

                # Waste data
                cursor.execute("""
                    SELECT w.waste_date, w.floor, w.meal, wd.food_item, wd.leftover_amount
                    FROM waste_summary w
                    JOIN waste_details wd ON w.waste_id = wd.waste_id
                    WHERE w.waste_date >= %s - INTERVAL 30 DAY
                """, (created_at,))
                waste_data = cursor.fetchall()

                # Feedback data
                cursor.execute("""
                    SELECT fs.feedback_date, fs.meal, fs.mess, fd.food_item, fd.rating
                    FROM feedback_summary fs
                    JOIN feedback_details fd ON fs.feedback_id = fd.feedback_id
                    WHERE fs.feedback_date >= %s - INTERVAL 30 DAY
                """, (created_at,))
                feedback_data = cursor.fetchall()

            result = (waste_data, feedback_data)
            cache.set(cache_key, result)
            return result

        except Exception as e:
            logging.error(f"Error fetching waste+feedback for {mess_name}: {e}")
            cache.set(cache_key, ([], []))
            return [], []
    
    @classmethod
    def get_waste_summary(cls) -> Tuple[List[Dict], float]:
        """Get waste summary with caching"""
        cache_key = "waste_summary"
        
        # Try cache first
        cached_data = cache_manager.waste_cache.get(cache_key, cache_manager.WASTE_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        waste_data = []
        max_waste_value = 1  # default to avoid divide by zero
        
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()
                cursor.execute("""
                    SELECT floor, SUM(total_waste) AS total_waste
                    FROM waste_summary
                    WHERE waste_date >= %s - INTERVAL 30 DAY
                    GROUP BY floor
                    ORDER BY floor
                """, (created_at,))
                waste_data = cursor.fetchall()

                # Convert Decimal to float
                for row in waste_data:
                    row['total_waste'] = float(row['total_waste'])

                if waste_data:
                    max_waste_value = max(row['total_waste'] for row in waste_data)
                    if max_waste_value == 0:
                        max_waste_value = 1

            result = (waste_data, max_waste_value)
            cache_manager.waste_cache.set(cache_key, result)
            return result

        except Exception as e:
            logging.error(f"Waste summary error: {e}")
            return [], 1
    
    @classmethod
    def get_waste_feedback_data(cls, mess_name: str) -> Tuple[List[Dict], List[Dict]]:
        """Get waste and feedback data for analysis with caching"""
        cache_key = f"waste_feedback_{mess_name}"
        
        # Try cache first
        cached_data = cache_manager.waste_cache.get(cache_key, cache_manager.WASTE_TTL)
        if cached_data is not None:
            return cached_data
        
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()

                # Waste data
                cursor.execute("""
                    SELECT w.waste_date, w.floor, w.meal, wd.food_item, wd.leftover_amount
                    FROM waste_summary w
                    JOIN waste_details wd ON w.waste_id = wd.waste_id
                    WHERE w.waste_date >= %s - INTERVAL 30 DAY
                """, (created_at,))
                waste_data = cursor.fetchall()

                # Feedback data
                cursor.execute("""
                    SELECT fs.feedback_date, fs.meal, fs.mess, fd.food_item, fd.rating
                    FROM feedback_summary fs
                    JOIN feedback_details fd ON fs.feedback_id = fd.feedback_id
                    WHERE fs.feedback_date >= %s - INTERVAL 30 DAY
                """, (created_at,))
                feedback_data = cursor.fetchall()

            result = (waste_data, feedback_data)
            cache_manager.waste_cache.set(cache_key, result)
            return result

        except Exception as e:
            logging.error(f"Error fetching waste+feedback for {mess_name}: {e}")
            return [], []
    
    @classmethod
    def submit_waste_data(cls, waste_date, meal: str, floor: str, total_waste: float,
                         prepared_amounts: Dict[str, int], leftover_amounts: Dict[str, int]) -> bool:
        """Submit waste data"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Check for existing data
                cursor.execute("""
                    SELECT COUNT(*) FROM waste_summary 
                    WHERE waste_date = %s AND meal = %s AND floor = %s
                """, (waste_date, meal, floor))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    logging.warning(f"Waste data already exists for {waste_date}, {meal}, {floor}")
                    return False
                
                # Insert waste summary
                cursor.execute("""
                    INSERT INTO waste_summary (waste_date, meal, floor, total_waste)
                    VALUES (%s, %s, %s, %s)
                """, (waste_date, meal, floor, total_waste))
                waste_id = cursor.lastrowid
                
                # Insert waste details
                for food_item in prepared_amounts:
                    cursor.execute("""
                        INSERT INTO waste_details (waste_id, food_item, prepared_amount, leftover_amount)
                        VALUES (%s, %s, %s, %s)
                    """, (waste_id, food_item, prepared_amounts[food_item], leftover_amounts[food_item]))
                
                connection.commit()
                
                # Clear cache
                cls.clear_waste_cache()
                return True
                
        except Exception as e:
            logging.error(f"Waste data submission error: {e}")
            return False
    
    @classmethod
    def clear_waste_feedback_cache(cls, mess_name: str):
        """Clear cache for waste+feedback for a specific mess"""
        cache_key = f"waste_feedback_{mess_name}"
        cache_manager.get_cache('waste_feedback').clear(cache_key)
    
    @classmethod
    def clear_waste_summary_cache(cls):
        """Clear cached waste summary"""
        cache_manager.get_cache('waste_summary').clear("waste_summary")
    
    @classmethod
    def clear_waste_cache(cls):
        """Clear waste-related caches"""
        cache_manager.waste_cache.clear()
