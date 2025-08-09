"""
Admin routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, get_current_meal, is_odd_week
import logging

admin_bp = Blueprint('admin', __name__)


def require_admin_login():
    """Decorator to require admin login"""
    if 'admin_id' not in session or session.get('role') != 'admin':
        flash("Please log in as an admin to access this page.", 'error')
        return redirect(url_for('auth.login'))
    return None


@admin_bp.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    toggle_status = False
    enabled_time = None
    
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("SELECT is_enabled, enabled_at FROM feature_toggle LIMIT 1")
            toggle = cursor.fetchone()
            if toggle:
                toggle_status = toggle['is_enabled']
                enabled_time = toggle.get('enabled_at')
                enabled_time = enabled_time.strftime('%B %d') if enabled_time else None
                
    except Exception as e:
        logging.error(f"Admin dashboard error: {e}")
    
    return render_template('admin/dashboard.html', 
                         enabled_time=enabled_time, 
                         mess_switch_enabled=toggle_status)


@admin_bp.route('/select-mess', methods=['GET', 'POST'])
def select_mess():
    """Mess selection for admin"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        selected_mess = request.form.get('selected_mess')
        
        if selected_mess in ['mess1', 'mess2']:
            session['admin_mess'] = selected_mess
            mess_name = 'Mess Sai' if selected_mess == 'mess1' else 'Mess Sheila'
            flash(f"{mess_name} selected successfully!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid mess selection. Please try again.", "error")
    
    return render_template('admin/select_mess.html')


@admin_bp.route('/toggle-mess-switch', methods=['POST'])
def toggle_mess_switch():
    """Toggle mess switching feature"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            # Get current toggle status
            cursor.execute("SELECT is_enabled, enabled_at FROM feature_toggle LIMIT 1")
            toggle = cursor.fetchone()
            
            if not toggle:
                flash('Feature toggle record not found.', 'error')
                return redirect(url_for('admin.dashboard'))
            
            created_at = get_fixed_time().strftime('%Y-%m-%d %H:%M:%S')
            current_status = toggle['is_enabled']
            enabled_time = toggle.get('enabled_at')
            
            if current_status:
                # Turn OFF and process requests
                cursor.execute("""
                    UPDATE feature_toggle
                    SET is_enabled = FALSE, disabled_at = %s, enabled_at = NULL
                """, (created_at,))
                
                if enabled_time:
                    # Process switch requests
                    cursor.execute("""
                        SELECT s_id, desired_mess 
                        FROM mess_switch_requests 
                        WHERE created_at BETWEEN %s AND %s
                    """, (enabled_time, created_at))
                    requests = cursor.fetchall()
                    
                    for req in requests:
                        cursor.execute("""
                            UPDATE student SET mess = %s WHERE s_id = %s
                        """, (req['desired_mess'], req['s_id']))
                    
                    cursor.execute("DELETE FROM mess_switch_requests WHERE created_at < %s", (enabled_time,))
                
                flash("Mess switching feature has been turned OFF and pending requests have been processed.", "info")
            else:
                # Turn ON
                cursor.execute("""
                    UPDATE feature_toggle
                    SET is_enabled = TRUE, enabled_at = %s, disabled_at = NULL
                """, (created_at,))
                flash("Mess switching feature has been turned ON", "success")
            
            connection.commit()
            
    except Exception as e:
        logging.error(f"Toggle mess switch error: {e}")
        flash('Something went wrong while updating the feature toggle.', 'error')
    
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/send-notification', methods=['GET', 'POST'])
def send_notification():
    """Send notifications to users"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        recipient_type = request.form.get('recipient_type', '').strip()
        
        if not message or recipient_type not in ['student', 'mess_official', 'both']:
            flash("Invalid input!", "error")
            return redirect(url_for('admin.dashboard'))
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = get_fixed_time()
                cursor.execute("""
                    INSERT INTO notifications (message, recipient_type, created_at) 
                    VALUES (%s, %s, %s)
                """, (message, recipient_type, created_at))
                connection.commit()
                flash("Notification sent successfully!", "success")
                
        except Exception as e:
            logging.error(f"Send notification error: {e}")
            flash("Error sending notification.", "error")
    
    return render_template('admin/send_notification.html')


@admin_bp.route('/update-veg-menu', methods=['GET', 'POST'])
def update_veg_menu():
    """Update vegetarian menu"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    week_type = 'Odd' if is_odd_week() else 'Even'
    day = get_fixed_time().strftime('%A')
    meal = get_current_meal()
    
    if request.method == 'POST':
        food_items = request.form.getlist('food_item[]')
        food_items = [item.strip() for item in food_items if item.strip()]
        
        if not food_items:
            flash('Please enter valid food items.', 'error')
            return redirect(url_for('admin.update_veg_menu'))
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Clear previous data
                cursor.execute("""
                    DELETE FROM temporary_menu 
                    WHERE week_type=%s AND day=%s AND meal=%s
                """, (week_type, day, meal))
                
                # Insert new data
                for item in food_items:
                    cursor.execute("""
                        INSERT INTO temporary_menu (week_type, day, meal, food_item, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (week_type, day, meal, item, get_fixed_time()))
                
                connection.commit()
                flash('Veg menu updated temporarily for today.', 'success')
                
        except Exception as e:
            logging.error(f"Update veg menu error: {e}")
            flash('Error updating menu.', 'error')
        
        return redirect(url_for('admin.update_veg_menu'))
    
    return render_template('admin/update_veg_menu.html', 
                         week_type=week_type, 
                         day=day, 
                         meal=meal)


@admin_bp.route('/restore-default-veg-menu', methods=['POST'])
def restore_default_veg_menu():
    """Restore default vegetarian menu"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            week_type = 'Odd' if is_odd_week() else 'Even'
            day = get_fixed_time().strftime('%A')
            meal = get_current_meal()
            
            cursor.execute("""
                DELETE FROM temporary_menu 
                WHERE week_type=%s AND day=%s AND meal=%s
            """, (week_type, day, meal))
            
            if cursor.rowcount > 0:
                flash('Veg menu restored to default.', 'success')
            else:
                flash('No temporary menu found to restore.', 'info')
            
            connection.commit()
            
    except Exception as e:
        logging.error(f"Restore default menu error: {e}")
        flash('Error restoring menu.', 'error')
    
    return redirect(url_for('admin.update_veg_menu'))


@admin_bp.route('/feedback-summary')
def feedback_summary():
    """Feedback summary for admin"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session.get('admin_mess')
    if not mess_name:
        return redirect(url_for('admin.select_mess'))
    
    feedback_summary_data = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT s.feedback_date, s.meal, COUNT(DISTINCT s.s_id) AS total_students, 
                       AVG(d.rating) AS avg_rating
                FROM feedback_summary s
                JOIN feedback_details d ON s.feedback_id = d.feedback_id
                WHERE mess = %s
                GROUP BY s.feedback_date, s.meal
                ORDER BY s.feedback_date DESC
            """, (mess_name,))
            feedback_summary_data = cursor.fetchall()
            
    except Exception as e:
        logging.error(f"Feedback summary error: {e}")
        flash("Error loading feedback data.", "error")
    
    return render_template('admin/feedback_summary.html', 
                         feedback_summary_data=feedback_summary_data)

@admin_bp.route('/feedback-details/<feedback_date>/<meal>')
def feedback_detail(feedback_date, meal):
    """Feedback details for a specific date and meal"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response

    mess_name = session.get('admin_mess')
    if not mess_name:
        flash("Please select a mess.", "error")
        return redirect(url_for('admin.select_mess'))

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

    except Exception as e:
        logging.error(f"Error fetching feedback details: {e}")
        flash("Error loading feedback details.", "error")
        return redirect(url_for('admin.feedback_summary'))

    return render_template('admin/feedback_details.html',
                           feedback_data=feedback_data,
                           feedback_date=feedback_date,
                           meal=meal)


@admin_bp.route('/student-feedback/<s_id>/<feedback_date>/<meal>')
def student_feedback(s_id, feedback_date, meal):
    """Detailed feedback for a specific student"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response

    mess_name = session.get('admin_mess')
    if not mess_name:
        flash("Please select a mess.", "error")
        return redirect(url_for('admin.select_mess'))

    feedback_details = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT fd.food_item, fd.rating, fd.comments
                FROM feedback_summary fs
                JOIN feedback_details fd ON fs.feedback_id = fd.feedback_id
                WHERE fs.s_id = %s 
                  AND fs.feedback_date = %s 
                  AND fs.meal = %s 
                  AND mess = %s
            """, (s_id, feedback_date, meal, mess_name))
            feedback_details = cursor.fetchall()

    except Exception as e:
        logging.error(f"Error fetching student feedback: {e}")
        flash("Error loading student feedback.", "error")
        return redirect(url_for('admin.feedback_detail', 
                                feedback_date=feedback_date, 
                                meal=meal))

    return render_template('admin/student_feedback_details.html',
                           feedback_details=feedback_details,
                           s_id=s_id,
                           feedback_date=feedback_date,
                           meal=meal)


@admin_bp.route('/waste-summary')
def waste_summary():
    """Waste summary for admin"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response

    waste_data = []
    max_waste_value = 1  # Avoid division by zero

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

            # 🔧 Convert Decimal to float to avoid Jinja type errors
            for row in waste_data:
                row['total_waste'] = float(row['total_waste'])

            # ✅ Calculate max value safely
            if waste_data:
                max_waste_value = max(row['total_waste'] for row in waste_data)
                if max_waste_value == 0:
                    max_waste_value = 1  # Prevent divide by zero

    except Exception as e:
        logging.error(f"Waste summary error: {e}")
        flash("Error loading waste data.", "error")

    return render_template(
        'admin/waste_summary.html',
        waste_data=waste_data,
        max_waste_value=max_waste_value
    )



@admin_bp.route('/payment-summary')
def payment_summary():
    """Payment summary for admin"""
    redirect_response = require_admin_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session.get('admin_mess')
    if not mess_name:
        flash("Select mess first", "error")
        return redirect(url_for('admin.select_mess'))
    
    summary_data = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            created_at = get_fixed_time().date()
            cursor.execute("""
                SELECT payment_date, GROUP_CONCAT(food_item SEPARATOR ', ') AS food_item, 
                       meal, SUM(amount) AS total_amount
                FROM payment
                WHERE mess = %s AND payment_date >= %s - INTERVAL 30 DAY
                GROUP BY payment_date, meal
                ORDER BY payment_date DESC
            """, (mess_name, created_at))
            summary_data = cursor.fetchall()
            
    except Exception as e:
        logging.error(f"Admin payment summary error: {e}")
        flash("Error loading payment data.", "error")
    
    return render_template('admin/payment_summary.html', 
                         summary_data=summary_data, 
                         mess_name=mess_name)
