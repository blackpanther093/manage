"""
Menu-related services for ManageIt application
"""
import logging
from typing import Optional, List, Tuple
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class MenuService:
    """Service class for menu operations"""
    
    @classmethod
    def get_menu(cls, date=None, meal=None) -> Tuple[Optional[str], List[str]]:
        """Get menu with caching"""
        current_meal = meal or TimeUtils.get_current_meal()
        cache_key = f"menu_{current_meal}_{date or 'today'}"
        
        # Try cache first
        cached_data = cache_manager.menu_cache.get(cache_key, cache_manager.MENU_TTL)
        if cached_data:
            return cached_data
        
        # Fetch from database
        try:
            menu_data = cls._fetch_menu_from_db(date, current_meal)
            cache_manager.menu_cache.set(cache_key, menu_data)
            # print("DEBUG: Fetched menu from DB")
            return menu_data
        except Exception as e:
            logging.error(f"Error fetching menu: {e}")
            return None, [], None
    
    @classmethod
    def _fetch_menu_from_db(cls, date=None, meal=None) -> Tuple[Optional[str], List[str]]:
        """Fetch menu from database"""
        try:
            date = date or TimeUtils.get_fixed_time().date()
            meal = meal or TimeUtils.get_current_meal()

            if not meal:
                return None, [], None

            week_type = 'Odd' if TimeUtils.is_odd_week(date) else 'Even'
            day = date.strftime('%A')

            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Get veg menu (temporary or default)
                cursor.execute("""
                    SELECT distinct food_item FROM temporary_menu
                    WHERE week_type = %s AND day = %s AND meal = %s
                """, (week_type, day, meal))
                temp_menu = cursor.fetchall()
                veg_menu_items = [item[0] for item in temp_menu] if temp_menu else []

                if not veg_menu_items:
                    cursor.execute("""
                        SELECT distinct food_item FROM menu
                        WHERE week_type = %s AND day = %s AND meal = %s
                    """, (week_type, day, meal))
                    veg_menu_items = [item[0] for item in cursor.fetchall()]

                weekday = TimeUtils.get_fixed_time().strftime('%A')
        
                cursor.execute("""
                    SELECT d.food_item, ROUND(AVG(d.rating), 2) AS avg_rating
                    FROM feedback_details d
                    JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                    JOIN menu m ON d.food_item = m.food_item  
                    WHERE m.day = %s AND m.week_type = %s AND m.meal = %s
                    GROUP BY d.food_item
                    ORDER BY avg_rating DESC
                    LIMIT 1
                """,(weekday, week_type, meal))
                top_rated = cursor.fetchone()
                if top_rated:
                    top_rated_item = top_rated[0]
                    
            return meal, veg_menu_items, top_rated_item if top_rated else None

        except Exception as e:
            logging.error(f"Error fetching menu from database: {e}")
            return None, [], None
    
    @classmethod
    def get_non_veg_menu(cls, mess_name: str, date=None, meal=None) -> List[Tuple]:
        """Get non-veg menu with caching"""
        date = date or TimeUtils.get_fixed_time().date()
        meal = meal or TimeUtils.get_current_meal()
        
        if not meal:
            return []

        cache_key = f"non_veg_{mess_name}_{date}_{meal}"
        
        # Try cache first
        cached_data = cache_manager.non_veg_cache.get(cache_key, cache_manager.MENU_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            # print("DEBUG: Fetching non-veg menu from DB")
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT distinct food_item, MIN(cost)
                    FROM non_veg_menu_items
                    JOIN non_veg_menu_main 
                    ON non_veg_menu_items.menu_id = non_veg_menu_main.menu_id
                    WHERE menu_date = %s AND meal = %s AND mess = %s
                    GROUP BY food_item
                """, (date, meal, mess_name))
                data = cursor.fetchall()
                
                cache_manager.non_veg_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Error fetching non-veg menu for {mess_name}: {e}")
            cache_manager.non_veg_cache.set(cache_key, [])
            return []
    
    @classmethod
    def clear_menu_cache(cls):
        """Clear menu-related caches"""
        cache_manager.menu_cache.clear()
        cache_manager.non_veg_cache.clear()
    
    @classmethod
    def get_amount_data(cls, food_item: str, mess_name: str, date=None, meal=None) -> Optional[Tuple]:
        """Get amount data for food item with caching"""
        date = date or TimeUtils.get_fixed_time().date()
        meal = meal or TimeUtils.get_current_meal()
        
        if not meal or not food_item or not mess_name:
            return None

        cache_key = f"amount_{food_item}_{mess_name}_{date}_{meal}"
        
        # Try cache first
        cached_data = cache_manager.payment_cache.get(cache_key, cache_manager.PAYMENT_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT n.item_id, n.cost 
                    FROM non_veg_menu_items n
                    JOIN non_veg_menu_main m ON n.menu_id = m.menu_id
                    WHERE n.food_item = %s AND m.menu_date = %s 
                    AND m.meal = %s AND m.mess = %s
                """, (food_item, date, meal, mess_name))
                data = cursor.fetchone()
                
                cache_manager.payment_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Error fetching amount data for {food_item}: {e}")
            cache_manager.payment_cache.set(cache_key, None)
            return None
