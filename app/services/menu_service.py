"""
Menu-related services for ManageIt application
"""
import logging
from typing import Optional, List, Tuple
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager
from datetime import timedelta

MEAL_ORDER = ["Breakfast", "Lunch", "Snacks", "Dinner"]

class MenuService:
    """Service class for menu operations"""
    
    @classmethod
    def _get_meals_to_fetch(cls, current_meal: str, date):
        """Return [(meal, date), ...] depending on current meal."""
        idx = MEAL_ORDER.index(current_meal)

        if current_meal == "Dinner":
            tomorrow = date + timedelta(days=1)
            return [(MEAL_ORDER[idx], date), ("Breakfast", tomorrow)]
        else:
            return [(m, date) for m in MEAL_ORDER[idx:]]

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
    def _fetch_menu_from_db(cls, date=None, meal=None):
        try:
            date = date or TimeUtils.get_fixed_time().date()
            meal = meal or TimeUtils.get_current_meal()
            if not meal:
                return None, {}, None

            week_type = 'Odd' if TimeUtils.is_odd_week(date) else 'Even'
            meals_to_fetch = cls._get_meals_to_fetch(meal, date)

            menus = {}
            top_rated_item = None

            with DatabaseManager.get_db_cursor() as (cursor, connection):
                for m, d in meals_to_fetch:
                    day = d.strftime('%A')

                    veg_items = []

                    # ✅ Temporary menu check only for current meal
                    if m == meal:
                        # Current meal → check temporary menu
                        cursor.execute("""
                            SELECT DISTINCT food_item FROM temporary_menu
                            WHERE week_type = %s AND day = %s AND meal = %s
                        """, (week_type, day, m))
                        temp_menu = cursor.fetchall()
                        veg_items = [item[0] for item in temp_menu] if temp_menu else []

                        # Fallback to permanent menu if temp empty
                        if not veg_items:
                            cursor.execute("""
                                SELECT DISTINCT food_item FROM menu
                                WHERE week_type = %s AND day = %s AND meal = %s
                            """, (week_type, day, m))
                            veg_items = [item[0] for item in cursor.fetchall()]

                    else:
                        # Non-current meals → always use permanent menu
                        cursor.execute("""
                            SELECT DISTINCT food_item FROM menu
                            WHERE week_type = %s AND day = %s AND meal = %s
                        """, (week_type, day, m))
                        veg_items = [item[0] for item in cursor.fetchall()]

                    menus[m] = veg_items

                    # ✅ Top-rated item only for current meal
                    if m == meal:
                        cursor.execute("""
                            SELECT d.food_item, ROUND(AVG(d.rating), 2) AS avg_rating
                            FROM feedback_details d
                            JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                            JOIN menu m2 ON d.food_item = m2.food_item  
                            WHERE m2.day = %s AND m2.week_type = %s AND m2.meal = %s
                            GROUP BY d.food_item
                            ORDER BY avg_rating DESC
                            LIMIT 1
                        """, (day, week_type, m))
                        top_rated = cursor.fetchone()
                        if top_rated:
                            top_rated_item = top_rated[0]
            # print(f"Menu fetched for {meal}: {menus}")
            return meal, menus, top_rated_item

        except Exception as e:
            logging.error(f"Error fetching menu from database: {e}")
            return None, {}, None

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
