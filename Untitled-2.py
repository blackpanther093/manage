"""
Utility functions for ManageIt application
"""
from datetime import datetime, timezone
import pytz
import mysql.connector
from app.models.database import DatabaseManager
from app.models.feedback_classifier import classify_feedback
import logging
import smtplib
from email.mime.text import MIMEText
from flask import current_app, url_for
# import time
import threading
import requests
import markdown
# from threading import Lock

_cache_lock = threading.RLock()

_cached_menu_meal = None
_cached_menu_data = None  # Tuple: (meal, veg_menu_items, non_veg_menu1, non_veg_menu2)
_cached_menu_timestamp = None

_cached_rating_meal = None
_cached_avg_ratings = None  # Tuple: (count1, avg1, count2, avg2)
_cached_rating_timestamp = None

# CACHE_TTL_SECONDS = 60 * 60  # 1 hour TTL (optional, mostly relies on meal changes)

def get_fixed_time():
    """Get current time in IST timezone"""
    utc_now = datetime.now(timezone.utc)
    ist = pytz.timezone("Asia/Kolkata")
    return utc_now.astimezone(ist)

def seconds_until_next_meal():
    now = get_fixed_time()
    hour = now.hour
    minute = now.minute
    total_minutes = hour * 60 + minute

    # Meal boundaries in minutes
    boundaries = [
        0,          # Breakfast start
        11 * 60,    # Lunch start
        16 * 60,    # Snacks start
        18 * 60 + 30, # Dinner start
        24 * 60     # End of day
    ]

    for b in boundaries:
        if b > total_minutes:
            return (b - total_minutes) * 60  # seconds until next boundary
    
    # If somehow no boundary found (e.g. at end of day), return 1 hour as fallback
    return 3600

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
        # with DatabaseManager.get_db_cursor() as (cursor, connection):
        #     current_date = get_fixed_time().date()
            
        #     # Clean old data
        #     cursor.execute("DELETE FROM temporary_menu WHERE created_at < %s", (current_date,))
        #     cursor.execute("""
        #         DELETE FROM non_veg_menu_items 
        #         WHERE menu_id IN (
        #             SELECT menu_id FROM non_veg_menu_main 
        #             WHERE menu_date < %s
        #         )
        #     """, (current_date,))
        #     cursor.execute("DELETE FROM non_veg_menu_main WHERE menu_date < %s", (current_date,))
        #     connection.commit()
        pass
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

def get_menu_cached(date=None, meal=None):
    """Fetch menu details based on date and meal, using non-veg cache."""
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

        # ✅ Use cached fetch for non-veg menus
        # non_veg_menu1 = get_non_veg_menu("mess1", date, meal)
        # non_veg_menu2 = get_non_veg_menu("mess2", date, meal)

        return meal, veg_menu_items

    except Exception as e:
        logging.error(f"Error fetching menu: {e}")
        return None, []

def avg_rating_cached():
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

CACHE_TTL_SECONDS = seconds_until_next_meal()

def get_menu(date=None, meal=None):
    global _cached_menu_meal, _cached_menu_data, _cached_menu_timestamp
    
    current_meal = meal or get_current_meal()
    now = get_fixed_time().timestamp()
    
    with _cache_lock:
        # Cache expired if:
        # - no cache
        # - meal changed since last cache
        # - TTL expired (optional safety)
        if (_cached_menu_meal  != current_meal
            or _cached_menu_data is None
            or _cached_menu_timestamp is None
            or now - _cached_menu_timestamp > CACHE_TTL_SECONDS):
            
            # Refresh cache by calling original DB query
            menu_data = get_menu_cached(date=date, meal=current_meal)
            
            # Update cache
            _cached_menu_meal = current_meal
            _cached_menu_data = menu_data
            _cached_menu_timestamp = now
            
            return menu_data
        # print(f"Using cached menu for meal: {_cached_meal}")  # Debug log
        # Return cached data
        return _cached_menu_data

def avg_rating():
    global _cached_rating_meal, _cached_avg_ratings, _cached_rating_timestamp
    
    current_meal = get_current_meal()
    if not current_meal:
        return (0, 0.0, 0, 0.0)
    
    now = get_fixed_time().timestamp()
    
    with _cache_lock:
        if (_cached_rating_meal != current_meal
            or _cached_avg_ratings is None
            or _cached_rating_timestamp is None
            or now - _cached_rating_timestamp > CACHE_TTL_SECONDS):
            
            # Refresh cache by calling original DB query
            avg_ratings = avg_rating_cached()
            
            _cached_avg_ratings = avg_ratings
            _cached_rating_meal = current_meal
            _cached_rating_timestamp = now
            
            return avg_ratings
        
        return _cached_avg_ratings

def clear_menu_cache():
    global _cached_menu_meal, _cached_menu_data, _cached_menu_timestamp
    with _cache_lock:
        _cached_menu_meal = None
        _cached_menu_data = None
        _cached_menu_timestamp = None

def send_confirmation_email(recipient_email, token):
    """Send account confirmation email with token link."""
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    subject = "Confirm your ManageIt account"
    body = f"Hi,\n\nClick the link below to confirm your account:\n{confirm_url}\n\nIf you didn't request this, please ignore."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = recipient_email

    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        if current_app.config['MAIL_USE_TLS']:
            server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)

_cached_non_veg_menu = {}         # { "mess1": [...], "mess2": [...] }
_cached_non_veg_timestamp = {}    # { "mess1": timestamp, "mess2": timestamp }

def get_non_veg_menu(mess_name, date=None, meal=None):
    date = date or get_fixed_time().date()
    meal = meal or get_current_meal()
    if not meal:
        return []

    cache_key = f"{mess_name}_{date}_{meal}"
    now = get_fixed_time().timestamp()

    with _cache_lock:
        if (
            cache_key not in _cached_non_veg_menu
            or now - _cached_non_veg_timestamp.get(cache_key, 0) > CACHE_TTL_SECONDS
        ):
            try:
                with DatabaseManager.get_db_cursor() as (cursor, connection):
                    cursor.execute("""
                        SELECT food_item, MIN(cost)
                        FROM non_veg_menu_items
                        JOIN non_veg_menu_main 
                        ON non_veg_menu_items.menu_id = non_veg_menu_main.menu_id
                        WHERE menu_date = %s AND meal = %s AND mess = %s
                        GROUP BY food_item
                    """, (date, meal, mess_name))
                    data = cursor.fetchall()
                    _cached_non_veg_menu[cache_key] = data
                    _cached_non_veg_timestamp[cache_key] = now
            except Exception as e:
                logging.error(f"Error fetching non-veg menu for {mess_name}: {e}")
                _cached_non_veg_menu[cache_key] = []
        return _cached_non_veg_menu[cache_key]

def clear_non_veg_menu_cache(mess_name, date=None, meal=None):
    date = date or get_fixed_time().date()
    meal = meal or get_current_meal()
    cache_key = f"{mess_name}_{date}_{meal}"
    with _cache_lock:
        _cached_non_veg_menu.pop(cache_key, None)
        _cached_non_veg_timestamp.pop(cache_key, None)
    clear_amount_data_cache(mess_name=mess_name, date=date, meal=meal)

_cached_amount_data = {}
_cached_amount_timestamp = {}

def get_amount_data(food_item, mess_name, date=None, meal=None):
    """Fetch (item_id, cost) for a food item with caching."""
    date = date or get_fixed_time().date()
    meal = meal or get_current_meal()
    if not meal or not food_item or not mess_name:
        return None

    cache_key = f"{food_item}_{mess_name}_{date}_{meal}"
    now = get_fixed_time().timestamp()

    with _cache_lock:
        if (
            cache_key not in _cached_amount_data
            or now - _cached_amount_timestamp.get(cache_key, 0) > CACHE_TTL_SECONDS
        ):
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
                    _cached_amount_data[cache_key] = data
                    _cached_amount_timestamp[cache_key] = now
            except Exception as e:
                logging.error(f"Error fetching amount data for {food_item}: {e}")
                _cached_amount_data[cache_key] = None
        return _cached_amount_data[cache_key]

def clear_amount_data_cache(food_item=None, mess_name=None, date=None, meal=None):
    """Clear cached amount data (specific or all)."""
    with _cache_lock:
        if food_item and mess_name:
            date = date or get_fixed_time().date()
            meal = meal or get_current_meal()
            cache_key = f"{food_item}_{mess_name}_{date}_{meal}"
            _cached_amount_data.pop(cache_key, None)
            _cached_amount_timestamp.pop(cache_key, None)
        else:
            _cached_amount_data.clear()
            _cached_amount_timestamp.clear()

_cached_payment_summary = {}
_cached_payment_summary_timestamp = {}
# PAYMENT_SUMMARY_TTL = 60  # seconds

def get_payment_summary(mess_name):
    now = get_fixed_time().timestamp()
    cache_key = mess_name

    with _cache_lock:
        if (
            cache_key not in _cached_payment_summary
        ):
            created_at = get_fixed_time().date()
            try:
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
                    _cached_payment_summary[cache_key] = data
                    _cached_payment_summary_timestamp[cache_key] = now
            except Exception as e:
                logging.error(f"Payment summary error: {e}")
                _cached_payment_summary[cache_key] = []

        return _cached_payment_summary[cache_key]

def clear_payment_summary_cache(mess_name):
    with _cache_lock:
        _cached_payment_summary.pop(mess_name, None)
        _cached_payment_summary_timestamp.pop(mess_name, None)

_cache_data = {}  # { recipient_type: {"data": [...], "timestamp": float} }

def get_notifications(recipient_type):
    """Fetch notifications for a specific recipient type with caching."""
    now = get_fixed_time().timestamp()
    cached = _cache_data.get(recipient_type)

    if cached:
        return cached["data"]

    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT message, created_at 
                FROM notifications 
                WHERE recipient_type = %s
                AND created_at >= NOW() - INTERVAL 7 DAY 
                ORDER BY created_at DESC
            """, (recipient_type,))
            data = cursor.fetchall()

            _cache_data[recipient_type] = {"data": data, "timestamp": now}
            return data
    except Exception as e:
        logging.error(f"Error fetching {recipient_type} notifications: {e}")
        return []

def clear_notifications_cache(recipient_type):
    """Clear cache for a specific recipient type."""
    if recipient_type in _cache_data:
        del _cache_data[recipient_type]


_cached_leaderboard = None
_cached_leaderboard_timestamp = None
_cached_monthly_avg = None
_cached_monthly_avg_timestamp = None

def get_leaderboard_cached(mess_name, weekday, week_type):
    global _cached_leaderboard, _cached_leaderboard_timestamp
    now = get_fixed_time().timestamp()

    with _cache_lock:
        if (
            _cached_leaderboard is None
            or _cached_leaderboard_timestamp is None
            or now - _cached_leaderboard_timestamp > CACHE_TTL_SECONDS
        ):
            try:
                with DatabaseManager.get_db_cursor() as (cursor, connection):
                    cursor.execute("""
                        SELECT d.food_item, ROUND(AVG(d.rating), 2) as avg_rating
                        FROM feedback_details d
                        JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                        JOIN menu m ON d.food_item = m.food_item  
                        WHERE s.mess = %s AND m.day = %s AND m.week_type = %s
                        GROUP BY d.food_item
                        ORDER BY avg_rating DESC
                        LIMIT 5
                    """, (mess_name, weekday, week_type))
                    _cached_leaderboard = cursor.fetchall()
                    _cached_leaderboard_timestamp = now
            except Exception as e:
                logging.error(f"Error fetching leaderboard: {e}")
                _cached_leaderboard = []
        return _cached_leaderboard

def get_monthly_avg_ratings_cached():
    global _cached_monthly_avg, _cached_monthly_avg_timestamp
    now = get_fixed_time().timestamp()

    with _cache_lock:
        if (
            _cached_monthly_avg is None
            or _cached_monthly_avg_timestamp is None
            or now - _cached_monthly_avg_timestamp > CACHE_TTL_SECONDS
        ):
            try:
                with DatabaseManager.get_db_cursor() as (cursor, connection):
                    created_at = get_fixed_time().date()
                    cursor.execute("""
                        SELECT s.mess, ROUND(AVG(d.rating), 2) as avg_rating
                        FROM feedback_details d
                        JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                        WHERE d.created_at >= DATE_SUB(%s, INTERVAL 1 MONTH)
                        GROUP BY s.mess
                    """, (created_at,))
                    _cached_monthly_avg = cursor.fetchall()
                    _cached_monthly_avg_timestamp = now
            except Exception as e:
                logging.error(f"Error fetching monthly avg ratings: {e}")
                _cached_monthly_avg = []
        return _cached_monthly_avg


_waste_feedback_cache = {}  # { mess_name: {"data": {...}, "timestamp": ts} }
CACHE_TTL_24H = 86400  # 24 hours in seconds

def get_waste_feedback(mess_name):
    """Fetch waste + feedback analysis for a mess with caching (expires after 24h)."""
    now = get_fixed_time().timestamp()
    cached = _waste_feedback_cache.get(mess_name)

    # ✅ Return only if cache exists AND it's fresh
    if cached and (now - cached["timestamp"] <= CACHE_TTL_24H):
        return cached["data"]

    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            created_at = get_fixed_time().date()

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

        _waste_feedback_cache[mess_name] = {
            "data": (waste_data, feedback_data),
            "timestamp": now
        }
        return waste_data, feedback_data

    except Exception as e:
        logging.error(f"Error fetching waste+feedback for {mess_name}: {e}")
        return [], []

def clear_waste_feedback_cache(mess_name):
    """Clear cache for waste+feedback for a specific mess."""
    _waste_feedback_cache.pop(mess_name, None)

#mess switch request cache
# CACHE_TTL_24H = 86400  # 24 hours in seconds
_switch_activity_cache = {}  # { mess_name: {"data": (joined_students, left_students), "timestamp": float} }

def get_switch_activity(mess_name):
    """Fetch mess switch activity with caching (expires after 24h)."""
    now = get_fixed_time().timestamp()
    cached = _switch_activity_cache.get(mess_name)

    # ✅ Return cached data if it's still fresh
    if cached:
        return cached["data"]

    joined_students = []
    left_students = []
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("SELECT is_enabled FROM feature_toggle LIMIT 1")
            result = cursor.fetchone()
            entry = result['is_enabled'] if result else False

            if not entry:
                # Students joining this mess
                cursor.execute("""
                    SELECT s_id FROM mess_switch_requests WHERE desired_mess = %s
                """, (mess_name,))
                joined_rows = cursor.fetchall()
                joined_ids = [row['s_id'] for row in joined_rows]
                joined_students = [{'count': len(joined_ids), 's_id': joined_ids}]

                # Students leaving this mess
                cursor.execute("""
                    SELECT s_id FROM mess_switch_requests WHERE desired_mess != %s
                """, (mess_name,))
                left_rows = cursor.fetchall()
                left_ids = [row['s_id'] for row in left_rows]
                left_students = [{'count': len(left_ids), 's_id': left_ids}]

        # Store in cache
        _switch_activity_cache[mess_name] = {
            "data": (joined_students, left_students),
            "timestamp": now
        }

    except Exception as e:
        logging.error(f"Switch activity error: {e}")

    return joined_students, left_students

def clear_switch_activity_cache(mess_name):
    """Clear cache for mess switch activity."""
    _switch_activity_cache.pop(mess_name, None)

#toggle feature cache
_feature_toggle_cache = {}
# CACHE_EXPIRY_SECONDS = 24 * 3600  # 24 hours

def get_feature_toggle_status():
    """Fetch feature toggle (enabled_at, disabled_at) with 24h cache expiration."""
    now = get_fixed_time().timestamp()
    cached = _feature_toggle_cache.get('feature_toggle')

    # Return cached if fresh
    if cached:
        return cached['data']

    toggle = None
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("SELECT enabled_at, disabled_at FROM feature_toggle LIMIT 1")
            toggle = cursor.fetchone()
        
        # Store in cache
        _feature_toggle_cache['feature_toggle'] = {
            "data": toggle,
            "timestamp": now
        }
    except Exception as e:
        logging.error(f"Error fetching feature toggle status: {e}")

    return toggle

def clear_feature_toggle_cache():
    """Clear cached feature toggle status."""
    _feature_toggle_cache.pop('feature_toggle', None)

#admin feedback cache
_feedback_summary_cache = {}

def get_feedback_summary(mess_name):
    """Fetch feedback summary with caching (expires after 24h)."""
    now = get_fixed_time().timestamp()
    cached = _feedback_summary_cache.get(mess_name)
    dt = get_fixed_time().date()
    if cached:
        return cached['data']

    feedback_summary_data = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT s.feedback_date, s.meal, COUNT(DISTINCT s.s_id) AS total_students, 
                       AVG(d.rating) AS avg_rating
                FROM feedback_summary s
                JOIN feedback_details d ON s.feedback_id = d.feedback_id
                WHERE mess = %s and s.feedback_date >= %s - INTERVAL 30 DAY
                GROUP BY s.feedback_date, s.meal
                ORDER BY s.feedback_date DESC
            """, (mess_name, dt,))
            feedback_summary_data = cursor.fetchall()

        _feedback_summary_cache[mess_name] = {
            "data": feedback_summary_data,
            "timestamp": now
        }

    except Exception as e:
        logging.error(f"Feedback summary error for mess {mess_name}: {e}")

    return feedback_summary_data

def clear_feedback_summary_cache(mess_name):
    """Clear cached feedback summary for a mess."""
    _feedback_summary_cache.pop(mess_name, None)

#feedback details cache
_feedback_detail_cache = {}
CACHE_EXPIRY_SECONDS = 24 * 3600  # 24 hours

def get_feedback_detail(feedback_date, meal, mess_name):
    """Fetch feedback details with caching (expires after 24h)."""
    cache_key = (feedback_date, meal, mess_name)
    now = get_fixed_time().timestamp()
    cached = _feedback_detail_cache.get(cache_key)

    if cached and (now - cached['timestamp'] < CACHE_EXPIRY_SECONDS):
        return cached['data']

    feedback_data = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT fs.s_id, ROUND(AVG(fd.rating), 2) AS avg_rating
                FROM feedback_summary fs
                JOIN feedback_details fd ON fs.feedback_id = fd.feedback_id
                WHERE fs.feedback_date = %s AND fs.meal = %s AND mess = %s
                GROUP BY fs.s_id
                HAVING COUNT(fd.rating) > 0
            """, (feedback_date, meal, mess_name))
            feedback_data = cursor.fetchall()

        _feedback_detail_cache[cache_key] = {
            "data": feedback_data,
            "timestamp": now
        }

    except Exception as e:
        logging.error(f"Error fetching feedback details for {cache_key}: {e}")

    return feedback_data

def clear_feedback_detail_cache(feedback_date, meal, mess_name):
    """Clear cached feedback details for specific date, meal, and mess."""
    cache_key = (feedback_date, meal, mess_name)
    _feedback_detail_cache.pop(cache_key, None)

#waste details cache for admin
_waste_summary_cache = {}
CACHE_EXPIRY_SECONDS = 24 * 3600  # 24 hours

def get_waste_summary():
    """Fetch waste summary with caching (expires after 24h)."""
    now = get_fixed_time().timestamp()
    cached = _waste_summary_cache.get('waste_summary')

    if cached and (now - cached['timestamp'] < CACHE_EXPIRY_SECONDS):
        return cached['data']

    waste_data = []
    max_waste_value = 1  # default to avoid divide by zero
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            created_at = get_fixed_time().date()
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

        _waste_summary_cache['waste_summary'] = {
            "data": (waste_data, max_waste_value),
            "timestamp": now
        }

    except Exception as e:
        logging.error(f"Waste summary error: {e}")

    return waste_data, max_waste_value

def clear_waste_summary_cache():
    """Clear cached waste summary."""
    _waste_summary_cache.pop('waste_summary', None)

# Get today's critical feedbacks for admin dashboard
def get_today_critical_feedbacks():
    mess1_critical = []
    mess2_critical = []

    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            today_date = get_fixed_time().date()

            for mess, target_list in [('mess1', mess1_critical), ('mess2', mess2_critical)]:
                cursor.execute("""
                    SELECT detail_id, d.feedback_id, food_item, rating, comments, created_at
                    FROM feedback_details d 
                    JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                    WHERE DATE(created_at) = %s AND s.mess = %s
                    ORDER BY created_at ASC
                """, (today_date, mess))

                rows = cursor.fetchall()

                for row in rows:
                    text = (row.get('comments') or '').strip()
                    if text:
                        classification = classify_feedback(text)
                        if classification == "Critical":
                            row['classification'] = classification
                            target_list.append(row)

    except Exception as e:
        logging.error(f"Error fetching/classifying today's feedback: {e}")

    logging.info(f"Found {len(mess1_critical)} critical feedbacks for mess1 today.")
    logging.info(f"Found {len(mess2_critical)} critical feedbacks for mess2 today.")

    return mess1_critical, mess2_critical

def call_your_llm(prompt, api_key, model="llama-2-7b-chat", max_tokens=500, platform="groq"):
    """
    Calls Groq API with LLaMA model to get text completion (summary).

    Args:
        prompt (str): The input text prompt for the model.
        api_key (str): Your Groq API key.
        model (str): Model name, default is "llama-2-7b-chat".
        max_tokens (int): Max tokens in response.

    Returns:
        str: Generated text from model (summary).
    """
    url = platform

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
    "max_tokens": max_tokens,
    "temperature": 0.7,
    "top_p": 1,
    "n": 1,
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "model": model
    }


    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        # Assuming completion text is in choices[0].text or similar
        return data["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Groq API error {response.status_code}: {response.text}")

#Passing all critical feedbacks to the LLM for admin notification
def get_critical_feedback_texts_for_llm():
    mess1_feedbacks, mess2_feedbacks = get_today_critical_feedbacks()

    mess_wise_feedbacks = {
        "mess1": [],
        "mess2": []
    }

    for fb in mess1_feedbacks:
        comments = (fb.get('comments') or '').strip()
        if comments:
            mess_wise_feedbacks["mess1"].append(comments)

    for fb in mess2_feedbacks:
        comments = (fb.get('comments') or '').strip()
        if comments:
            mess_wise_feedbacks["mess2"].append(comments)

    combined_texts = {
        mess: "\n".join(comments) if comments else ""
        for mess, comments in mess_wise_feedbacks.items()
    }

    logging.info(f"Mess1 feedback (first 100 chars): {combined_texts['mess1'][:100]}...")
    logging.info(f"Mess2 feedback (first 100 chars): {combined_texts['mess2'][:100]}...")

    return combined_texts

def summarize_feedback_text(feedback_text):
    # Your LLM call here — example with pseudo-code
    # prompt = f"Summarize the following critical feedback comments given by students for the mess and suggest admin notification such that he gets all the insights from it:\n\n{feedback_text}"
    prompt = f"""
        You are generating a short, urgent **admin notification** based on student critical feedback.
        Rules:
        - Be brief and to the point (max 3–4 sentences).
        - Use a direct, alerting tone (no over-explanation).
        - Include only the key problem(s) without unnecessary details.
        - Keep it under 400 characters.

        Critical Feedback:
        {feedback_text}
    """

    api_key = current_app.config.get('GROQ_API_KEY')
    platform = current_app.config.get('GROQ_PLATFORM')
    model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    summary = call_your_llm(prompt, api_key, model=model, max_tokens=500, platform=platform)
    logging.info(f"Generated summary from LLM: {summary[:100]}...")  # Log first 100 chars
    return summary

MESS_NAME_MAP = {
    "mess1": "Food Sutra",
    "mess2": "Shakti"
}

def create_admin_notification_from_critical_feedback():
    combined_texts = get_critical_feedback_texts_for_llm()

    notifications = []
    for mess_key, feedback_text in combined_texts.items():
        if not feedback_text.strip():
            logging.warning(f"No critical feedback for {MESS_NAME_MAP[mess_key]}")
            continue

        summary = summarize_feedback_text(feedback_text)
        if not summary.strip():
            logging.warning(f"LLM returned empty summary for {MESS_NAME_MAP[mess_key]}, using raw feedback text instead.")
            summary = feedback_text

        summary_html = markdown.markdown(summary, extensions=["nl2br"])

        # Add mess name as heading in HTML
        mess_html_section = f"<h3>{MESS_NAME_MAP[mess_key]}</h3>\n{summary_html}"
        notifications.append(mess_html_section)

    return notifications


