"""
Student routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, get_current_meal, get_menu, is_odd_week, get_notifications, get_monthly_avg_ratings_cached, get_leaderboard_cached, get_non_veg_menu, get_feature_toggle_status, clear_feedback_summary_cache, clear_feedback_detail_cache
from app.services.feedback_service import FeedbackService  # Import the class containing submit_feedback
import logging

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
        
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Check feedback status
            cursor.execute("""
                SELECT DISTINCT s_id FROM feedback_summary 
                WHERE s_id = %s AND feedback_date = %s AND mess = %s AND meal = %s
            """, (student_id, created_at, mess_name, meal))
            feedback_given = cursor.fetchone() is not None
            feedback_status = "Feedback Submitted" if feedback_given else "Feedback Pending"
            
        # Cached leaderboard
        weekday = get_fixed_time().strftime('%A')
        week_type = 'odd' if is_odd_week() else 'even'
        leaderboard = get_leaderboard_cached(mess_name, weekday, week_type)

        # Cached monthly avg ratings
        monthly_avg_ratings = get_monthly_avg_ratings_cached()
        
        return render_template('student/dashboard.html',
                             greeting=greeting,
                             feedback_status=feedback_status,
                             leaderboard=leaderboard,
                             monthly_avg_ratings=monthly_avg_ratings)
                             
    except Exception as e:
        logging.error(f"Student dashboard error: {e}")
        flash("Error loading dashboard data.", 'error')
        return render_template('student/dashboard.html', 
                             greeting="Hello", 
                             feedback_status="Unknown",
                             leaderboard=[], 
                             monthly_avg_ratings=[])

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
            non_veg_menu1 = get_non_veg_menu('mess1')
            non_veg_menu2 = []
        else:
            non_veg_menu1 = []
            non_veg_menu2 = get_non_veg_menu('mess2')
        
        # Get menu items
        _, veg_menu_items, = get_menu()
        
        # Filter veg items
        exclusions = {'salt', 'sugar', 'ghee', 'podi', 'coffee', 'bbj', 'sprouts', 'curd', 'papad'}
        veg_items = [
            item for item in veg_menu_items 
            if item.lower() not in exclusions 
            and not any(keyword in item.lower() for keyword in ['banana', 'pickle', 'salad', 'cut fruit', 'sauce', 'chutney'])
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
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            created_at = get_fixed_time().date()
            cursor.execute("""
                SELECT mess, payment_date, meal, food_item, amount
                FROM payment
                WHERE payment_date >= %s - INTERVAL 30 DAY
                AND s_id = %s
                ORDER BY payment_date DESC
            """, (created_at, student_id))
            data = cursor.fetchall()
            
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
