"""
Main routes for ManageIt application
"""
from flask import Blueprint, render_template, redirect, url_for, session
from app.utils.helpers import get_menu, avg_rating, get_notifications, get_non_veg_menu, get_fixed_time
import time as pytime
from datetime import datetime, time
import logging
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/home')
def home():
    """Home page displaying current menu and ratings"""
    start_time = pytime.time()
    try:
        meal, veg_menu_items = get_menu() or (None, [])
        # logging.info(f"DEBUG get_menu() returned meal: {meal}, veg_menu_items: {veg_menu_items}")
        non_veg_menu1 = get_non_veg_menu("mess1")
        # logging.debug(f"non_veg_menu1: {non_veg_menu1}")
        non_veg_menu2 = get_non_veg_menu("mess2")
        # logging.debug(f"non_veg_menu2: {non_veg_menu2}")
        mess1_count, mess1_rating, mess2_count, mess2_rating = avg_rating()
        # logging.debug(f"Ratings: mess1_count={mess1_count}, mess1_rating={mess1_rating}, mess2_count={mess2_count}, mess2_rating={mess2_rating}")

        current_time = get_fixed_time().time()
        # logging.debug(f"Current time: {current_time}")  # << Add this

        # Define serving time intervals as tuples of (start_time, end_time)
        serving_intervals = [
            (time(7, 0), time(9, 0)),
            (time(12, 0), time(14, 0)),
            (time(17, 0), time(18, 0)),
            (time(19, 0), time(21, 0)),
        ]
        # logging.debug(f"Serving intervals: {serving_intervals}")  # << Add this

        is_serving = any(start <= current_time <= end for start, end in serving_intervals)
        # logging.debug(f"is_serving: {is_serving}")  # << Add this

        if not meal or (not veg_menu_items and not non_veg_menu1 and not non_veg_menu2):
            # logging.info(f"Home route loaded in {pytime.time() - start_time:.3f} seconds")
            return render_template("home.html", meal=None, is_serving=is_serving)
        
        # logging.info(f"Home route loaded in {pytime.time() - start_time:.3f} seconds")
        return render_template("home.html",
            meal=meal,
            veg_menu_items=veg_menu_items,
            non_veg_menu1=non_veg_menu1,
            non_veg_menu2=non_veg_menu2,
            current_avg_rating_mess1=mess1_rating,
            current_avg_rating_mess2=mess2_rating,
            mess1_count=mess1_count,
            mess2_count=mess2_count,
            is_serving=is_serving
        )
    except Exception as e:
        # logging.exception("Exception occurred in home route")
        # logging.info(f"Home route loaded in {pytime.time() - start_time:.3f} seconds (with error)")
        return render_template("home.html", meal=None, error="Unable to load menu data", is_serving=False)


@main_bp.route('/public-notifications')
def public_notifications():
    """Public notifications page"""
    notifications = get_notifications("both")  # or "public" if stored that way    
    return render_template("notifications.html", 
                         notifications=notifications, 
                         back_url='/home')
