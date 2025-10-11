"""
Student routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, get_current_meal, get_menu, is_odd_week, get_notifications, get_monthly_avg_ratings_cached, get_leaderboard_cached, get_non_veg_menu, get_feature_toggle_status, clear_feedback_summary_cache, clear_feedback_detail_cache, clear_poll_cache
from app.services.feedback_service import FeedbackService  # Import the class containing submit_feedback
from app.services.payment_service import PaymentService
import logging
# import time
from datetime import time

student_bp = Blueprint('student', __name__)

def require_student_login():
    """Decorator to require student login"""
    if 'student_id' not in session or session.get('role') != 'student':
        flash("Please log in as a student to access this page.", 'error')
        return redirect(url_for('auth.login'))
    return None

@student_bp.route('/dashboard')
def dashboard():
    """Student dashboard"""
    redirect_response = require_student_login()
    if redirect_response:
        return redirect_response
    
    try:
        student_id = session['student_id']
        mess_name = session['mess']
        meal = get_current_meal()
        created_at = get_fixed_time().date()
        
        # Greeting based on time
        current_hour = get_fixed_time().hour
        if current_hour < 12:
            greeting = 'Good Morning'
        elif current_hour < 17:
            greeting = 'Good Afternoon'
        else:
            greeting = 'Good Evening'
        
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

        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Check feedback status
            cursor.execute("""
                SELECT DISTINCT s_id FROM feedback_summary 
                WHERE s_id = %s AND feedback_date = %s AND mess = %s AND meal = %s
            """, (student_id, created_at, mess_name, meal))
            feedback_given = cursor.fetchone() is not None
            feedback_status = "Feedback Submitted" if feedback_given else "Feedback Pending"
            
            student_vote = None

            if(is_serving and meal):
                        # --- Get student's vote for current meal ---
                cursor.execute("""
                    SELECT vote FROM meal_poll
                    WHERE student_id = %s AND mess = %s AND meal = %s AND poll_date = %s
                """, (student_id, mess_name, meal, created_at))
                # print("Checking for existing vote...")
                result = cursor.fetchone()
                student_vote = result[0] if result else None  # Can be 'Like', 'Dislike', or None

        # Cached leaderboard
        weekday = get_fixed_time().strftime('%A')
        week_type = 'odd' if is_odd_week() else 'even'
        leaderboard = get_leaderboard_cached(mess_name, weekday, week_type)
        # print(f"leaderboard: {leaderboard}")  # << Add this

        # Cached monthly avg ratings
        monthly_avg_ratings = get_monthly_avg_ratings_cached()
        # print(f"monthly_avg_ratings: {monthly_avg_ratings}")  # << Add this
        # monthly_avg_ratings = [(k, monthly_avg_ratings.get(k)) for k in ['mess1', 'mess2']]

        return render_template('student/dashboard.html',
                             greeting=greeting,
                             feedback_status=feedback_status,
                             leaderboard=leaderboard,
                             monthly_avg_ratings=monthly_avg_ratings,
                             student_vote=student_vote,
                             meal=meal,
                             is_serving=is_serving)
                             
    except Exception as e:
        logging.error(f"Student dashboard error: {e}")
        flash("Error loading dashboard data.", 'error')
        return render_template('student/dashboard.html', 
                             greeting="Hello", 
                             feedback_status="Unknown",
                             leaderboard=[], 
                             monthly_avg_ratings=[],
                             student_vote=None,
                             meal=None,
                             is_serving=False)

@student_bp.route('/poll/vote', methods=['POST'])
def poll_vote():
    """Handle real-time voting for Like/Dislike"""
    redirect_response = require_student_login()
    if redirect_response:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    try:
        student_id = session['student_id']
        mess_name = session['mess']
        meal = get_current_meal()
        poll_date = get_fixed_time().date()
        created_at = get_fixed_time().strftime('%Y-%m-%d %H:%M:%S')
        vote = request.json.get('vote')  # 'Like' or 'Dislike'

        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Insert or update vote with fixed timestamp
            cursor.execute("""
                INSERT INTO meal_poll (student_id, mess, meal, vote, poll_date, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE vote = VALUES(vote), created_at = VALUES(created_at)
            """, (student_id, mess_name, meal, vote, poll_date, created_at))
            connection.commit()
        # ✅ Clear poll cache after successful vote
        clear_poll_cache(meal)
        # flash(f"Thanks! Your '{vote}' vote was recorded.", "success")
        return jsonify({"success": True, "vote": vote, "created_at": created_at})
    
    except Exception as e:
        logging.error(f"Poll vote error: {e}")
        # flash("Something went wrong while saving your vote.", "danger")
        return jsonify({"success": False, "error": str(e)}), 500

@student_bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Student feedback form"""
    redirect_response = require_student_login()
    if redirect_response:
        return redirect_response
    
    student_id = session['student_id']
    student_name = session['student_name']
    mess = session['mess']
    created_at = get_fixed_time().date()
    meal = get_current_meal()
    
    if not mess:
        flash("Error: Mess information not found.", 'error')
        return redirect(url_for('auth.login'))
    
    if not meal:
        flash("No meal available at the moment", "error")
        return redirect(url_for('student.dashboard'))
    
    try:
        # Time check for meal availability
        current_hour = get_fixed_time().hour
        if ((meal == 'Breakfast' and current_hour < 7) or 
            (meal == 'Lunch' and current_hour < 12) or 
            (meal == 'Snacks' and current_hour < 17) or 
            (meal == 'Dinner' and current_hour < 19)):
            meal = None
            flash("No meal available at the moment", "error")
            return redirect(url_for('student.dashboard'))
        
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Check if feedback already given
            cursor.execute(""" 
                SELECT DISTINCT s_id FROM feedback_summary 
                WHERE s_id = %s AND feedback_date = %s AND mess = %s AND meal = %s
            """, (student_id, created_at, mess, meal))
            
            if cursor.fetchone():
                flash("Feedback already submitted for today.", "error")
                return redirect(url_for('main.home'))
                    
        if mess == 'mess1':
            non_veg_menu1, _, _ = get_non_veg_menu('mess1')
            non_veg_menu2 = []
        else:
            non_veg_menu1 = []
            non_veg_menu2, _, _ = get_non_veg_menu('mess2')
        
        # Get menu items
        _, veg_menu_items, _ = get_menu()
        
        # Filter veg items
        exclusions = {'salt', 'sugar', 'ghee', 'podi', 'coffee', 'bbj', 'sprouts', 'curd', 'papad'}
        veg_items = [
            item for item in veg_menu_items 
            if item.lower() not in exclusions 
            and not any(keyword in item.lower() for keyword in ['banana', 'pickle', 'salad', 'cut fruit', 'sauce', 'chutney', 'raita', 'boost', 'coffee'])
        ]
        
        if request.method == 'POST':
            try:
                # Collect ratings and comments
                food_ratings = {}
                comments = {}
                non_veg_menu = non_veg_menu1 if mess == 'mess1' else non_veg_menu2
                menu_items = veg_items + non_veg_menu
                
                for item in menu_items:
                    rating = request.form.get(f'rating_{item}')
                    comment = request.form.get(f'comment_{item}')
                    if rating:
                        food_ratings[item] = int(rating)
                        comments[item] = comment or None
                
                if not food_ratings:
                    flash("No ratings submitted. Please provide at least one rating.", "error")
                    return redirect(url_for('student.feedback'))
                
                # Call the submit_feedback class method
                feedback_success = FeedbackService.submit_feedback(
                    student_id=student_id,
                    feedback_date=created_at,
                    meal=meal,
                    mess=mess,
                    food_ratings=food_ratings,
                    comments=comments
                )
                
                if feedback_success:
                    flash("Feedback submitted successfully!", "success")
                    return redirect(url_for('student.dashboard'))
                else:
                    flash("An error occurred while submitting feedback.", "error")
                    return redirect(url_for('student.feedback'))
                    
            except Exception as e:
                logging.error(f"Feedback submission error: {e}")
                flash("An error occurred while submitting feedback.", "error")
    
    except Exception as e:
        logging.error(f"Feedback page error: {e}")
        flash("Error loading feedback form.", "error")
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/feedback.html',
                         meal=meal,
                         veg_menu_items=veg_items,
                         non_veg_menu1=non_veg_menu1,
                         non_veg_menu2=non_veg_menu2,
                         student_name=student_name,
                         mess=mess)

@student_bp.route('/payment-history')
def payment_history():
    """Student payment history"""
    redirect_response = require_student_login()
    if redirect_response:
        return redirect_response
    
    student_id = session['student_id']
    mess_name = session['mess']
    
    try:
        data = PaymentService.get_student_payment_history(student_id, days=30)
            
    except Exception as e:
        logging.error(f"Payment history error: {e}")
        flash("Error loading payment history.", "error")
        data = []
    
    return render_template('student/payment_history.html', 
                         data=data, 
                         mess_name=mess_name)

@student_bp.route('/switch-mess', methods=['POST'])
def switch_mess():
    """Handle mess switching request"""
    redirect_response = require_student_login()
    if redirect_response:
        return redirect_response
    
    student_id = session['student_id']
    current_mess = session['mess']
    desired_mess = 'mess2' if current_mess == 'mess1' else 'mess1'
    mess_name = 'Mess Food Sutra' if desired_mess == 'mess1' else 'Mess Shakti'
    toggle = get_feature_toggle_status()

    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            # Check feature toggle
            
            if not toggle or not toggle['enabled_at']:
                flash("Mess switching feature is not currently active.", "error")
                return redirect(url_for('auth.profile'))
            
            enabled_at = toggle['enabled_at']
            disabled_at = toggle['disabled_at']
            now = get_fixed_time().replace(tzinfo=None)
            
            if now < enabled_at or disabled_at is not None:
                flash("Mess switching is currently not allowed.", "error")
                return redirect(url_for('auth.profile'))
            
            # Check existing request
            cursor.execute("SELECT created_at FROM mess_switch_requests WHERE s_id = %s", (student_id,))
            existing_request = cursor.fetchone()
            
            if existing_request:
                request_time = existing_request['created_at']
                if request_time >= enabled_at:
                    flash("Your mess switch request is already under consideration.", "error")
                    return redirect(url_for('auth.profile'))
                else:
                    cursor.execute("DELETE FROM mess_switch_requests WHERE s_id = %s", (student_id,))
            
            # Check capacity
            cursor.execute("SELECT capacity, current_capacity FROM mess_data WHERE mess = %s", (desired_mess,))
            mess_data = cursor.fetchone()
            if not mess_data:
                flash(f"Mess data not found for {mess_name}.", "error")
                return redirect(url_for('auth.profile'))

            mess_capacity = mess_data['capacity']
            
            # cursor.execute("SELECT COUNT(*) AS count FROM student WHERE mess = %s", (desired_mess,))
            mess_count = mess_data['current_capacity']
            
            if mess_count >= mess_capacity:
                flash(f"{mess_name} has reached its maximum capacity.", "error")
                return redirect(url_for('auth.profile'))
            
            # Insert request
            created_at = now.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO mess_switch_requests (s_id, desired_mess, created_at)
                VALUES (%s, %s, %s)
            """, (student_id, desired_mess, created_at))
            connection.commit()
            
            flash("Your mess switch request has been submitted successfully.", "success")
            
    except Exception as e:
        logging.error(f"Mess switch error: {e}")
        flash("An error occurred while processing your request.", "error")
    
    return redirect(url_for('auth.profile'))

@student_bp.route('/notifications')
def notifications():
    """Student notifications"""
    redirect_response = require_student_login()
    if redirect_response:
        return redirect_response
    
    notifications = get_notifications("student")
    
    return render_template("notifications.html", 
                         notifications=notifications, 
                         back_url='/student/dashboard')
