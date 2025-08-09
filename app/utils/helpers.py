"""
Utility functions for ManageIt application
"""
from datetime import datetime, timezone
import pytz
import mysql.connector
from app.models.database import DatabaseManager
import logging


def get_fixed_time():
    """Get current time in IST timezone"""
    utc_now = datetime.now(timezone.utc)
    ist = pytz.timezone("Asia/Kolkata")
    return utc_now.astimezone(ist)


def is_odd_week(date=None):
    """Determine if the given date falls in an odd or even week"""
    if date is None:
        date = get_fixed_time().date()
    
    start_date = datetime(2025, 7, 27).date()
    days_difference = (date - start_date).days
    return (days_difference // 7) % 2 == 0


def get_current_meal(hour=None):
    """Get current meal based on time and clean old data"""
    try:
        # Clean old temporary menu and non-veg items
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            current_date = get_fixed_time().date()
            
            # Clean old data
            cursor.execute("DELETE FROM temporary_menu WHERE created_at < %s", (current_date,))
            cursor.execute("""
                DELETE FROM non_veg_menu_items 
                WHERE menu_id IN (
                    SELECT menu_id FROM non_veg_menu_main 
                    WHERE menu_date < %s
                )
            """, (current_date,))
            cursor.execute("DELETE FROM non_veg_menu_main WHERE menu_date < %s", (current_date,))
            connection.commit()
            
    except Exception as e:
        logging.error(f"Error cleaning old menu data: {e}")
    
    # Determine current meal
    if hour is None:
        hour = get_fixed_time().hour
        minute = get_fixed_time().minute
        total_time = hour * 60 + minute
    
    if 0 <= total_time < 11*60:
        return "Breakfast"
    elif 11*60 <= total_time < 16*60:
        return "Lunch"
    elif 16*60 <= total_time <= 18*60 + 30:
        return "Snacks"
    elif 18*60 + 30 < total_time <= 23*60 + 59:
        return "Dinner"
    return None


def get_menu(date=None, meal=None):
    """Fetch menu details based on date and meal"""
    try:
        date = date or get_fixed_time().date()
        meal = meal or get_current_meal()
        
        if not meal:
            return None, [], [], []
        
        week_type = 'Odd' if is_odd_week(date) else 'Even'
        day = date.strftime('%A')
        
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Get veg menu (temporary or default)
            cursor.execute("""
                SELECT food_item FROM temporary_menu
                WHERE week_type = %s AND day = %s AND meal = %s
            """, (week_type, day, meal))
            temp_menu = cursor.fetchall()
            veg_menu_items = [item[0] for item in temp_menu] if temp_menu else []
            
            if not veg_menu_items:
                cursor.execute("""
                    SELECT food_item FROM menu
                    WHERE week_type = %s AND day = %s AND meal = %s
                """, (week_type, day, meal))
                veg_menu_items = [item[0] for item in cursor.fetchall()]
            
            # Get non-veg menus
            cursor.execute("""
                SELECT food_item, MIN(cost)
                FROM non_veg_menu_items
                JOIN non_veg_menu_main ON non_veg_menu_items.menu_id = non_veg_menu_main.menu_id
                WHERE menu_date = %s AND meal = %s AND mess='mess1'
                GROUP BY food_item
            """, (date, meal))
            non_veg_menu1 = cursor.fetchall()
            
            cursor.execute("""
                SELECT food_item, MIN(cost)
                FROM non_veg_menu_items
                JOIN non_veg_menu_main ON non_veg_menu_items.menu_id = non_veg_menu_main.menu_id
                WHERE menu_date = %s AND meal = %s AND mess='mess2'
                GROUP BY food_item
            """, (date, meal))
            non_veg_menu2 = cursor.fetchall()
            
            return meal, veg_menu_items, non_veg_menu1, non_veg_menu2
            
    except Exception as e:
        logging.error(f"Error fetching menu: {e}")
        return None, [], [], []


def avg_rating():
    """Get average ratings for both messes"""
    meal = get_current_meal()
    if not meal:
        return (0, 0.0, 0, 0.0)

    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            created_at = get_fixed_time().date()

            results = {}

            for mess in ['mess1', 'mess2']:
                # Average rating query
                cursor.execute("""
                    SELECT AVG(rating) AS avg_rating
                    FROM feedback_details d
                    JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                    WHERE s.meal = %s AND s.mess = %s AND DATEDIFF(%s, s.feedback_date) % 14 = 0
                """, (meal, mess, created_at))
                avg = cursor.fetchone() or {"avg_rating": 0.0}

                # Count query
                cursor.execute("""
                    SELECT COUNT(*) AS count
                    FROM feedback_summary
                    WHERE meal = %s AND mess = %s AND DATEDIFF(%s, feedback_date) % 14 = 0
                """, (meal, mess, created_at))
                count = cursor.fetchone() or {"count": 0}

                results[mess] = {
                    'avg_rating': round(avg['avg_rating'] or 0.0, 2),
                    'count': count['count'] or 0
                }

            return (
                results['mess1']['count'], results['mess1']['avg_rating'],
                results['mess2']['count'], results['mess2']['avg_rating']
            )

    except Exception as e:
        logging.error(f"Error fetching average ratings: {e}")
        return (0, 0.0, 0, 0.0)
