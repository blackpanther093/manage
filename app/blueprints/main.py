"""
Main routes for ManageIt application
"""
from flask import Blueprint, render_template, redirect, url_for, session
from app.utils.helpers import get_menu, avg_rating

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/home')
def home():
    """Home page displaying current menu and ratings"""
    try:
        meal, veg_menu_items, non_veg_menu1, non_veg_menu2 = get_menu() or (None, [], [], [])
        mess1_count, mess1_rating, mess2_count, mess2_rating = avg_rating()
        
        if not meal or (not veg_menu_items and not non_veg_menu1 and not non_veg_menu2):
            return render_template("home.html", meal=None)
        
        return render_template("home.html",
            meal=meal,
            veg_menu_items=veg_menu_items,
            non_veg_menu1=non_veg_menu1,
            non_veg_menu2=non_veg_menu2,
            current_avg_rating_mess1=mess1_rating,
            current_avg_rating_mess2=mess2_rating,
            mess1_count=mess1_count,
            mess2_count=mess2_count
        )
    except Exception as e:
        return render_template("home.html", meal=None, error="Unable to load menu data")


@main_bp.route('/public-notifications')
def public_notifications():
    """Public notifications page"""
    from app.models.database import DatabaseManager
    
    notifications = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT message, created_at 
                FROM notifications 
                WHERE recipient_type IN ('both') 
                AND created_at >= NOW() - INTERVAL 7 DAY 
                ORDER BY created_at DESC
            """)
            notifications = cursor.fetchall()
    except Exception as e:
        pass  # Fail silently for public page
    
    return render_template("notifications.html", 
                         notifications=notifications, 
                         back_url='/home')
