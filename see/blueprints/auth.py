"""
Authentication routes for ManageIt application
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.database import DatabaseManager
from app.utils.helpers import send_confirmation_email
from app.utils.security import security_manager  # Added security manager import
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
        
        if security_manager.is_device_blocked(user_id):
            flash("Access denied. Too many failed attempts.", 'error')
            return render_template('auth/login.html')
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Check student
                cursor.execute("SELECT s_id, name, mess, password FROM student WHERE BINARY s_id = %s", (user_id,))
                student = cursor.fetchone()
                
                if student and check_password_hash(student[3], password):
                    security_manager.clear_failed_attempts(user_id)
                    security_manager.create_session(user_id, 'student', {
                        'student_name': student[1],
                        'mess': student[2]
                    })
                    
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
                    security_manager.clear_failed_attempts(user_id)
                    security_manager.create_session(user_id, 'mess_official', {
                        'mess': mess_official[1]
                    })
                    
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
                    security_manager.clear_failed_attempts(user_id)
                    security_manager.create_session(user_id, 'admin', {
                        'admin_name': admin[1]
                    })
                    
                    session.update({
                        'admin_id': admin[0],
                        'admin_name': admin[1],
                        'role': 'admin'
                    })
                    return redirect(url_for('admin.dashboard'))
                
                security_manager.record_failed_login(user_id)
                flash("Invalid ID or Password.", 'error')
                
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash("An error occurred during login. Please try again.", 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        mess_choice = request.form.get('mess', '').strip()  # mess1 / mess2
        password = request.form.get('password', '').strip()

        if not email.endswith('@iiitdm.ac.in'):
            flash("Only institute students are allowed.", 'error')
            return render_template('auth/signup.html')

        if not all([email, name, mess_choice, password]):
            flash("Please fill in all fields.", 'error')
            return render_template('auth/signup.html')

        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                cursor.execute("SELECT s_id FROM student WHERE mail = %s", (email,))
                if cursor.fetchone():
                    flash("Account already exists.", 'error')
                    return render_template('auth/signup.html')

                # Generate token with signup data
                serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                token = serializer.dumps({
                    'email': email,
                    'name': name,
                    'mess_choice': mess_choice,
                    'password': generate_password_hash(password)
                })

                send_confirmation_email(email, token)
                flash("A confirmation email has been sent. Please check your inbox.", 'success')
                return redirect(url_for('auth.signup'))
            
        except Exception as e:
            logging.error(f"Signup error: {e}")
            flash("Error during signup. Try again.", 'error')
            return redirect(url_for('auth.signup'))
        
    return render_template('auth/signup.html')

@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, max_age=120)  # 2 min expiry
    except SignatureExpired:
        flash("The confirmation link has expired.", 'error')
        return redirect(url_for('auth.signup'))
    except BadSignature:
        flash("Invalid confirmation link.", 'error')
        return redirect(url_for('auth.signup'))

    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            # Capacity check
            cursor.execute("SELECT capacity, current_capacity FROM mess_data WHERE mess = %s", (data['mess_choice'],))
            mess_data = cursor.fetchone()
            if not mess_data:
                flash("Selected mess not found.", 'error')
                return redirect(url_for('auth.signup'))

            capacity, current_capacity = mess_data
            assigned_mess = data['mess_choice']
            if current_capacity >= capacity:
                other_mess = 'mess2' if assigned_mess == 'mess1' else 'mess1'
                cursor.execute("SELECT capacity, current_capacity FROM mess_data WHERE mess_id = %s", (other_mess,))
                other_data = cursor.fetchone()
                if other_data and other_data[1] < other_data[0]:
                    assigned_mess = other_mess
                    flash(f"Selected mess is full. Assigned to {assigned_mess} instead.", 'info')
                else:
                    flash("All messes are full.", 'error')
                    return redirect(url_for('auth.signup'))

            # Insert confirmed student
            student_id = data['email'].split('@')[0]
            cursor.execute("""
                INSERT INTO student (s_id, name, mess, password, mail)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_id, data['name'], assigned_mess, data['password'], data['email']))

            cursor.execute("""
                UPDATE mess_data
                SET current_capacity = current_capacity + 1
                WHERE mess_id = %s
            """, (assigned_mess,))

            connection.commit()

        security_manager.create_session(student_id, 'student', {
            'student_name': data['name'],
            'mess': assigned_mess
        })

        session.update({
            'student_id': student_id,
            'student_name': data['name'],
            'mess': assigned_mess,
            'role': 'student'
        })

        flash("Your account has been confirmed! Welcome to your dashboard.", 'success')
        return redirect(url_for('student.dashboard'))
    
    except Exception as e:
        logging.error(f"Email confirmation error: {e}")
        flash("Error confirming account.", 'error')
        return redirect(url_for('auth.signup'))

@auth_bp.route('/logout')
def logout():
    """User logout handler"""
    security_manager.invalidate_session()
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
            return redirect(url_for('auth.profile'))  # Ends execution here
            
        except Exception as e:
            logging.error(f"Password update error: {e}")
            flash("An error occurred while updating password.", 'error')
            return render_template('auth/update_password.html')  # Return immediately here

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
