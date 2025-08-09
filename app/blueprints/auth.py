"""
Authentication routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.database import DatabaseManager
import logging

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login handler"""
    # Redirect if already logged in
    if session.get('role') == 'student':
        return redirect(url_for('student.dashboard'))
    elif session.get('role') == 'mess_official':
        return redirect(url_for('mess.dashboard'))
    elif session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        user_id = request.form.get('id', '').strip()
        password = request.form.get('password', '').strip()
        
        if not user_id or not password:
            flash("Please enter both ID and password.", 'error')
            return render_template('auth/login.html')
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Check student
                cursor.execute("SELECT s_id, name, mess, password FROM student WHERE BINARY s_id = %s", (user_id,))
                student = cursor.fetchone()
                
                if student and check_password_hash(student[3], password):
                    session.update({
                        'student_id': student[0],
                        'student_name': student[1],
                        'mess': student[2],
                        'role': 'student'
                    })
                    return redirect(url_for('student.dashboard'))
                
                # Check mess official
                cursor.execute("SELECT mess_id, mess, password FROM mess_data WHERE BINARY mess_id = %s", (user_id,))
                mess_official = cursor.fetchone()
                
                if mess_official and check_password_hash(mess_official[2], password):
                    session.update({
                        'mess_id': mess_official[0],
                        'mess': mess_official[1],
                        'role': 'mess_official'
                    })
                    return redirect(url_for('mess.dashboard'))
                
                # Check admin
                cursor.execute("SELECT admin_id, username, password FROM admin WHERE BINARY admin_id = %s", (user_id,))
                admin = cursor.fetchone()
                
                if admin and check_password_hash(admin[2], password):
                    session.update({
                        'admin_id': admin[0],
                        'admin_name': admin[1],
                        'role': 'admin'
                    })
                    return redirect(url_for('admin.dashboard'))
                
                flash("Invalid ID or Password.", 'error')
                
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash("An error occurred during login. Please try again.", 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """User logout handler"""
    session.clear()
    flash("You have been logged out successfully.", 'success')
    return redirect(url_for('main.home'))

@auth_bp.route('/update-password', methods=['GET', 'POST'])
def update_password():
    """Password update handler"""
    if 'role' not in session:
        flash("Please log in to update your password.", 'error')
        return redirect(url_for('auth.login'))
    
    role = session['role']
    if role == 'mess_official':
        user_id = session.get('mess_id')
    elif role == 'admin':
        user_id = session.get('admin_id')
    else:  # Default to student
        user_id = session.get('student_id')
    
    if not user_id:
        flash("Session error. Please log in again.", 'error')
        return redirect(url_for('auth.login'))
    
    table_mapping = {
        'student': ('student', 's_id'),
        'mess_official': ('mess_data', 'mess_id'),
        'admin': ('admin', 'admin_id')
    }
    
    if role not in table_mapping:
        flash("Invalid user role.", 'error')
        return redirect(url_for('auth.login'))
    
    table_name, user_column = table_mapping[role]
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not all([current_password, new_password, confirm_password]):
            flash("All fields are required.", 'error')
            return render_template('auth/update_password.html')
        
        if new_password != confirm_password:
            flash("New password and confirm password do not match.", 'error')
            return render_template('auth/update_password.html')
        
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", 'error')
            return render_template('auth/update_password.html')
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute(f"SELECT password FROM {table_name} WHERE {user_column} = %s", (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data or not check_password_hash(user_data[0], current_password):
                    flash("Current password is incorrect.", 'error')
                    return render_template('auth/update_password.html')
                
                new_password_hash = generate_password_hash(new_password)
                cursor.execute(
                    f"UPDATE {table_name} SET password = %s WHERE {user_column} = %s", 
                    (new_password_hash, user_id)
                )
                connection.commit()
                
            flash("Password updated successfully!", 'success')
            return redirect(url_for('auth.profile'))  # ✅ Ends execution here
            
        except Exception as e:
            logging.error(f"Password update error: {e}")
            flash("An error occurred while updating password.", 'error')
            return render_template('auth/update_password.html')  # ✅ Return immediately here

    return render_template('auth/update_password.html')

@auth_bp.route('/profile')
def profile():
    """User profile page"""
    role = session.get('role')
    
    if not role:
        flash("Please log in to access your profile.", 'error')
        return redirect(url_for('auth.login'))
    
    # Get user data based on role
    user_data = {}
    mess_switch_enabled = False
    
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
            if role == 'student':
                user_id = session.get('student_id')
                cursor.execute("SELECT s_id, name, mess FROM student WHERE s_id = %s", (user_id,))
                user_data = cursor.fetchone()
                
                # Check mess switch toggle
                cursor.execute("SELECT is_enabled FROM feature_toggle LIMIT 1")
                toggle = cursor.fetchone()
                mess_switch_enabled = toggle and toggle['is_enabled']
                
            elif role == 'mess_official':
                user_id = session.get('mess_id')
                cursor.execute("SELECT mess_id, mess FROM mess_data WHERE mess_id = %s", (user_id,))
                user_data = cursor.fetchone()
                
            elif role == 'admin':
                user_id = session.get('admin_id')
                cursor.execute("SELECT admin_id, username FROM admin WHERE admin_id = %s", (user_id,))
                user_data = cursor.fetchone()
            
            if not user_data:
                flash("User data not found.", 'error')
                return redirect(url_for('auth.login'))
                
    except Exception as e:
        logging.error(f"Profile error: {e}")
        flash("Error loading profile data.", 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', 
                         user_data=user_data, 
                         role=role, 
                         mess_switch_enabled=mess_switch_enabled)
