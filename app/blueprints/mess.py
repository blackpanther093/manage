"""
Mess official routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, get_current_meal, get_menu, is_odd_week
import pandas as pd
import plotly.express as px
import logging
from datetime import timedelta

mess_bp = Blueprint('mess', __name__)


def require_mess_login():
    """Decorator to require mess official login"""
    if 'mess_id' not in session or session.get('role') != 'mess_official':
        flash("Please log in as a mess official to access this page.", 'error')
        return redirect(url_for('auth.login'))
    return None


@mess_bp.route('/dashboard')
def dashboard():
    """Mess official dashboard"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_id = session['mess_id']
    mess_name = session['mess']
    username = session.get('student_name', 'Mess Official')
    
    return render_template('mess/dashboard.html', 
                         mess_id=mess_id, 
                         mess_name=mess_name, 
                         username=username)


@mess_bp.route('/add-non-veg-menu', methods=['GET', 'POST'])
def add_non_veg_menu():
    """Add non-vegetarian menu items"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess = session.get('mess')
    meal, _, _, _ = get_menu()
    
    if not meal:
        flash("No meal available at the moment.", 'error')
        return redirect(url_for('main.home'))
    
    previous_items = []
    
    if request.method == 'POST':
        food_items = request.form.getlist('food_item[]')
        costs = request.form.getlist('cost[]')
        
        # Clean input
        food_items = [item.strip() for item in food_items if item.strip()]
        costs = [c.strip() for c in costs if c.strip()]
        
        if not food_items or not costs or len(food_items) != len(costs):
            flash("Invalid input. Ensure all fields are filled.", 'error')
            return redirect(url_for('mess.add_non_veg_menu'))
        
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                created_at = get_fixed_time().date()
                
                # Check for duplicates
                placeholders = ', '.join(['%s'] * len(food_items))
                query = f"""
                    SELECT food_item FROM non_veg_menu_items n
                    JOIN non_veg_menu_main m ON n.menu_id = m.menu_id
                    WHERE menu_date = %s AND meal = %s AND mess = %s 
                    AND LOWER(TRIM(food_item)) IN ({placeholders})
                """
                normalized_input = [item.lower().strip() for item in food_items]
                params = [created_at, meal, mess] + normalized_input
                cursor.execute(query, params)
                
                existing_items = {row['food_item'].strip().lower() for row in cursor.fetchall()}
                duplicates = [item for item in food_items if item.strip().lower() in existing_items]
                
                filtered_items_and_costs = [
                    (item, cost) for item, cost in zip(food_items, costs)
                    if item.strip().lower() not in existing_items
                ]
                
                if not filtered_items_and_costs:
                    flash(f"All items already exist: {', '.join(duplicates)}", 'error')
                    return redirect(url_for('mess.add_non_veg_menu'))
                
                if duplicates:
                    flash(f"Cannot insert duplicate food items: {', '.join(duplicates)}", 'error')
                
                # Insert menu
                cursor.execute("""
                    INSERT INTO non_veg_menu_main (menu_date, meal, mess)
                    VALUES (%s, %s, %s)
                """, (created_at, meal, mess))
                menu_id = cursor.lastrowid
                
                # Insert items
                for item, cost in filtered_items_and_costs:
                    cursor.execute("""
                        INSERT INTO non_veg_menu_items (menu_id, food_item, cost)
                        VALUES (%s, %s, %s)
                    """, (menu_id, item.strip(), cost.strip()))
                
                connection.commit()
                flash("Item(s) added successfully.", 'success')
                
        except Exception as e:
            logging.error(f"Add non-veg menu error: {e}")
            flash("An error occurred while adding the menu.", 'error')
        
        return redirect(url_for('mess.add_non_veg_menu'))
    
    # Load previous items
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            created_at = get_fixed_time().date()
            cursor.execute("""
                SELECT item_id, food_item, cost 
                FROM non_veg_menu_items i 
                JOIN non_veg_menu_main m ON i.menu_id = m.menu_id
                WHERE DATE(menu_date) = %s AND meal = %s AND mess = %s
            """, (created_at, meal, mess))
            previous_items = cursor.fetchall()
            
    except Exception as e:
        logging.error(f"Load previous menu error: {e}")
        flash("Unable to load existing menu items.", 'error')
    
    return render_template('mess/add_non_veg_menu.html', 
                         meal=meal, 
                         mess=mess, 
                         previous_items=previous_items)


@mess_bp.route('/delete-item', methods=['POST'])
def delete_item():
    """Delete non-veg menu item"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    item_id = request.form.get('item_id')
    if not item_id:
        flash("Error: Item not found", 'error')
        return redirect(url_for('mess.add_non_veg_menu'))
    
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("DELETE FROM non_veg_menu_items WHERE item_id = %s", (item_id,))
            connection.commit()
            flash('Item deleted successfully!', 'success')
            
    except Exception as e:
        logging.error(f"Delete item error: {e}")
        flash('An error occurred while deleting the item.', 'error')
    
    return redirect(url_for('mess.add_non_veg_menu'))


@mess_bp.route('/waste-feedback', methods=['GET', 'POST'])
def waste_feedback():
    """Waste feedback form"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess = session.get('mess')
    current_hour = get_fixed_time().hour
    meal, veg_menu_items, non_veg_menu1, non_veg_menu2 = get_menu()
    
    # Check meal availability
    if ((meal == 'Breakfast' and current_hour < 9) or 
        (meal == 'Lunch' and current_hour < 14) or 
        # (meal == 'Lunch' and current_hour < 13) or #testing 
        (meal == 'Snacks' and current_hour < 18) or 
        (meal == 'Dinner' and current_hour < 21)):
        meal = None
    
    if not meal:
        flash("No meal available at the moment.", 'error')
        return redirect(url_for('mess.dashboard'))
    
    # Filter veg items
    exclusions = {'salt', 'sugar', 'ghee', 'podi', 'coffee', 'bbj', 'sprouts', 'curd', 'papad', 'rasam', 'fryums', 'milk', 'tea'}
    veg_items = [
        item for item in veg_menu_items 
        if item.lower() not in exclusions 
        and not any(keyword in item.lower() for keyword in ['banana', 'pickle', 'salad', 'cut fruit', 'sauce', 'chutney', 'juice'])
    ]
    
    if request.method == 'POST':
        floor = request.form.get('floor')
        waste_amount = request.form.get('waste_amount')
        
        if floor not in ['Ground', 'First', 'Second', 'Third']:
            flash("Invalid floor.", 'error')
            return redirect(url_for('mess.waste_feedback'))
        
        prepared_amounts = {}
        leftover_amounts = {}
        
        # Determine menu based on floor
        if floor in ['Ground', 'First']:
            menu_items = veg_items + [item[0] for item in non_veg_menu1]
        else:
            menu_items = veg_items + [item[0] for item in non_veg_menu2]
        
        for food_item in menu_items:
            prepared = request.form.get(f'prepared_{food_item}')
            leftover = request.form.get(f'leftover_{food_item}')
            
            if prepared and leftover:
                try:
                    prepared_amounts[food_item] = int(prepared)
                    leftover_amounts[food_item] = int(leftover)
                except ValueError:
                    flash(f"Invalid input for {food_item}. Please enter numbers only.", 'error')
                    return redirect(url_for('mess.waste_feedback'))
        
        if not prepared_amounts:
            flash("No valid data submitted.", 'error')
            return redirect(url_for('mess.waste_feedback'))
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = get_fixed_time().date()
                
                # Check for existing data
                cursor.execute("""
                    SELECT COUNT(*) FROM waste_summary 
                    WHERE waste_date = %s AND meal = %s AND floor = %s
                """, (created_at, meal, floor))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    flash("Waste data already submitted for today.", 'error')
                    return redirect(url_for('mess.waste_feedback'))
                
                # Insert waste summary
                cursor.execute("""
                    INSERT INTO waste_summary (waste_date, meal, floor, total_waste)
                    VALUES (%s, %s, %s, %s)
                """, (created_at, meal, floor, waste_amount))
                waste_id = cursor.lastrowid
                
                # Insert waste details
                for food_item in prepared_amounts:
                    cursor.execute("""
                        INSERT INTO waste_details (waste_id, food_item, prepared_amount, leftover_amount)
                        VALUES (%s, %s, %s, %s)
                    """, (waste_id, food_item, prepared_amounts[food_item], leftover_amounts[food_item]))
                
                connection.commit()
                flash("Waste data submitted successfully!", 'success')
                return redirect(url_for('mess.dashboard'))
                
        except Exception as e:
            logging.error(f"Waste feedback error: {e}")
            flash("An error occurred while submitting waste data.", 'error')
    
    return render_template('mess/waste_feedback.html', 
                         meal=meal, 
                         veg_menu_items=veg_items,
                         non_veg_menu1=non_veg_menu1, 
                         non_veg_menu2=non_veg_menu2, 
                         mess=mess)


@mess_bp.route('/add-payment', methods=['GET', 'POST'])
def add_payment():
    """Add payment details"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session['mess']
    meal = get_current_meal()
    created_at = get_fixed_time().date()
    
    if request.method == 'POST':
        s_id = request.form.get('s_id', '').strip()
        food_item = request.form.get('food_item', '').strip()
        payment_mode = request.form.get('payment_mode', '').strip()
        
        if not all([s_id, food_item, payment_mode]):
            flash("All fields are required.", "error")
            return redirect(url_for('mess.add_payment'))
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Validate student
                cursor.execute("SELECT mess FROM student WHERE s_id = %s", (s_id,))
                student_data = cursor.fetchone()
                
                if not student_data or student_data[0] != mess_name:
                    flash("Invalid student ID or student not from your mess.", "error")
                    return redirect(url_for('mess.add_payment'))
                
                # Get food item cost
                cursor.execute("""
                    SELECT item_id, cost FROM non_veg_menu_items n
                    JOIN non_veg_menu_main m ON n.menu_id = m.menu_id
                    WHERE n.food_item = %s AND m.menu_date = %s 
                    AND m.meal = %s AND mess = %s
                """, (food_item, created_at, meal, mess_name))
                amount_data = cursor.fetchone()
                
                if not amount_data:
                    flash("Invalid food item selected.", "error")
                    return redirect(url_for('mess.add_payment'))
                
                item_id, amount = amount_data
                
                # Insert payment
                cursor.execute("""
                    INSERT INTO payment (s_id, mess, meal, payment_date, food_item, amount, payment_mode, item_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (s_id, mess_name, meal, created_at, food_item, amount, payment_mode, item_id))
                
                connection.commit()
                flash("Payment details entered successfully!", "success")
                
        except Exception as e:
            logging.error(f"Add payment error: {e}")
            flash("An error occurred while adding the payment.", "error")
        
        return redirect(url_for('mess.add_payment'))
    
    # Get available food items
    food_items = []
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT n.food_item, n.cost
                FROM non_veg_menu_items n
                JOIN non_veg_menu_main m ON n.menu_id = m.menu_id
                WHERE m.menu_date = %s AND m.meal = %s AND m.mess = %s
            """, (created_at, meal, mess_name))
            food_items = cursor.fetchall()
            
    except Exception as e:
        logging.error(f"Get food items error: {e}")
    
    return render_template('mess/add_payment.html', 
                         food_items=food_items, 
                         meal=meal, 
                         mess_name=mess_name)


@mess_bp.route('/payment-summary')
def payment_summary():
    """Payment summary for mess officials"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session.get('mess')
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
        logging.error(f"Payment summary error: {e}")
        flash("An error occurred while fetching payment data.", "error")
    
    return render_template('mess/payment_summary.html', 
                         summary_data=summary_data, 
                         mess_name=mess_name)


@mess_bp.route('/switch-activity')
def switch_activity():
    """Mess switch activity"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session['mess']
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
                
    except Exception as e:
        logging.error(f"Switch activity error: {e}")
    
    return render_template('mess/switch_activity.html',
                         mess_name=mess_name,
                         joined_students=joined_students,
                         left_students=left_students)


@mess_bp.route('/notifications')
def notifications():
    """Mess official notifications"""
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session['mess']
    notifications = []
    
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            created_at = get_fixed_time().date()
            
            # Get general notifications
            cursor.execute("""
                SELECT message, created_at FROM notifications 
                WHERE recipient_type IN ('mess_official', 'both') 
                AND created_at >= %s - INTERVAL 7 DAY 
                ORDER BY created_at DESC
            """, (created_at,))
            notifications.extend([(row[0], row[1]) for row in cursor.fetchall()])
            
            # High waste warnings
            floors = ['Ground', 'First'] if mess_name == 'mess1' else ['Second', 'Third']
            cursor.execute("""
                SELECT floor, SUM(total_waste) as total_waste, waste_date 
                FROM waste_summary 
                WHERE waste_date >= %s - INTERVAL 7 DAY 
                AND (floor = %s OR floor = %s)
                GROUP BY floor, waste_date
                HAVING SUM(total_waste) > 50
                ORDER BY waste_date DESC
            """, (created_at, floors[0], floors[1]))
            
            for floor, waste, date in cursor.fetchall():
                notifications.append((f"⚠️ High waste recorded on {floor} Floor with {waste} Kg.", date))
            
            # Low feedback alerts
            cursor.execute("""
                SELECT AVG(d.rating), s.meal, s.feedback_date 
                FROM feedback_details d
                JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                WHERE mess = %s AND s.feedback_date >= %s - INTERVAL 7 DAY
                GROUP BY s.meal, s.feedback_date
                HAVING AVG(d.rating) < 3.0
                ORDER BY s.feedback_date DESC
            """, (mess_name, created_at))
            
            for rating, meal, date in cursor.fetchall():
                notifications.append((f"❗ Low feedback detected for {meal} on {date} with Avg. Rating {round(rating, 2)}", date))
                
    except Exception as e:
        logging.error(f"Mess notifications error: {e}")
    
    return render_template("notifications.html", 
                         notifications=notifications, 
                         back_url='/mess/dashboard')

@mess_bp.route('/review-waste-feedback')
def review_waste_feedback():
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response


    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):

            created_at = get_fixed_time().date()
            current_meal = get_current_meal()
            # Fetch waste and feedback from last 30 days
            cursor.execute("""
                SELECT w.waste_date, w.floor, w.meal, wd.food_item, wd.leftover_amount
                FROM waste_summary w
                JOIN waste_details wd ON w.waste_id = wd.waste_id
                WHERE w.waste_date >= %s - INTERVAL 30 DAY
            """, (created_at,))
            waste_data = cursor.fetchall()

            cursor.execute("""
                SELECT fs.feedback_date, fs.meal, fs.mess, fd.food_item, fd.rating
                FROM feedback_summary fs
                JOIN feedback_details fd ON fs.feedback_id = fd.feedback_id
                WHERE fs.feedback_date >= %s - INTERVAL 30 DAY
            """, (created_at,))
            feedback_data = cursor.fetchall()

            connection.close()

            if not waste_data or not feedback_data:
                return render_template('mess/review_waste_feedback.html', no_data=True)

            # Convert to DataFrames
            waste_df = pd.DataFrame(waste_data)
            feedback_df = pd.DataFrame(feedback_data)

            # Normalize date using IST
            today = pd.Timestamp(get_fixed_time().replace(tzinfo=None)).normalize()
            waste_df['waste_date'] = pd.to_datetime(waste_df['waste_date']).dt.normalize()
            feedback_df['feedback_date'] = pd.to_datetime(feedback_df['feedback_date']).dt.normalize()
            waste_df['day_name'] = waste_df['waste_date'].dt.day_name()
            feedback_df['day_name'] = feedback_df['feedback_date'].dt.day_name()


            feedback_df['week_type'] = feedback_df['feedback_date'].apply(lambda x: 'Odd' if is_odd_week(x.date()) else 'Even')

            days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            feedback_df['day_name'] = pd.Categorical(feedback_df['day_name'], categories=days_order, ordered=True)

            # Add mess column to waste_df
            waste_df['mess'] = waste_df['floor'].apply(lambda x: 'mess1' if x in ['Ground', 'First'] else 'mess2')

            # 📊 1. Pie chart: Floor-wise waste
            floor_pie = px.pie(waste_df, names='floor', values='leftover_amount', title='Waste Distribution by Floor')
            floor_pie_plot = floor_pie.to_html(full_html=False, config={'displayModeBar': False})

            # 📊 2. Bar chart: Mess1 vs Mess2 total waste
            mess_waste_df = waste_df.groupby('mess')['leftover_amount'].sum().reset_index()
            mess_waste = px.bar(mess_waste_df, x='mess', y='leftover_amount', title='Total Waste: Mess1 vs Mess2', color='mess')
            mess_waste_plot = mess_waste.to_html(full_html=False, config={'displayModeBar': False})

            #3. Line plot: Average feedback ratings by day
            # plots = {}

            # for mess_name in feedback_df['mess'].unique():
            mess_name = session['mess']
            mess_df = feedback_df[feedback_df['mess'] == mess_name]

            avg_ratings = mess_df.groupby(['week_type', 'day_name'], observed=True)['rating'].mean().reset_index()

            fig = px.line(
                avg_ratings,
                x='day_name',
                y='rating',
                color='week_type',
                markers=True,
                title=f"Average Feedback Ratings by Day ({mess_name})",
                labels={'rating': 'Average Rating', 'day_name': 'Day of Week', 'week_type': 'Week Type'},
                category_orders={'day_name': days_order}
            )
            fig.update_layout(yaxis=dict(range=[1, 5]))

            plots = fig.to_html(full_html=False, config={'displayModeBar': False})

            # return render_template('feedback_line_plot.html', plots=plots)

            # 📊 4. Top 5 most wasted food items
            min_date = waste_df['waste_date'].min().date()
            relevant_dates = []
            check_date = today.date() - timedelta(days=14)

            while check_date >= min_date:
                relevant_dates.append(check_date)
                check_date -= timedelta(days=14)

            same_menu_df = waste_df[
                (waste_df['waste_date'].dt.date.isin(relevant_dates)) &
                (waste_df['meal'] == current_meal)
            ]

            # Get top 5 wasted items
            top5_df = same_menu_df.groupby('food_item')['leftover_amount'].sum().sort_values(ascending=False).head(5)
            top5_waste_list = top5_df.reset_index().values.tolist()

            
            # ⏱️ Only include data that is a multiple of 14 days from today
            def is_multiple_of_14_days_ago(past_date, ref_date):
                delta = (ref_date - past_date).days
                return delta % 14 == 0 and 0 <= delta <= 30

            waste_df['use_for_prediction'] = waste_df['waste_date'].apply(lambda d: is_multiple_of_14_days_ago(d, today))
            feedback_df['use_for_prediction'] = feedback_df['feedback_date'].apply(lambda d: is_multiple_of_14_days_ago(d, today))

            waste_relevant = waste_df[waste_df['use_for_prediction']]
            feedback_relevant = feedback_df[feedback_df['use_for_prediction']]

            # Clean food and meal
            waste_relevant['food_item'] = waste_relevant['food_item'].str.strip().str.lower()
            waste_relevant['meal'] = waste_relevant['meal'].str.strip().str.lower()
            feedback_relevant['food_item'] = feedback_relevant['food_item'].str.strip().str.lower()
            feedback_relevant['meal'] = feedback_relevant['meal'].str.strip().str.lower()

            # Merge on food and meal only (ignore date)
            # merged_df = pd.merge(waste_relevant, feedback_relevant, on=['food_item', 'meal'], how='inner')
            # merged_df['waste_score'] = merged_df['leftover_amount'] * (6 - merged_df['rating'])

            # print("Waste dates considered:", waste_relevant['waste_date'].unique())
            # print("Feedback dates considered:", feedback_relevant['feedback_date'].unique())
            # print("🧪 Waste Items:", waste_relevant['food_item'].unique())
            # print("🧪 Feedback Items:", feedback_relevant['food_item'].unique())

            if not waste_relevant.empty and not feedback_relevant.empty:
                # Merge based on food item and meal only (ignore exact dates since it's cyclic)
                merged_df = pd.merge(waste_relevant, feedback_relevant, on=['food_item', 'meal'], how='inner')
                # merged_df['waste_score'] = merged_df['leftover_amount'] * (6 - merged_df['rating'])
                if not merged_df.empty:
                    merged_df['waste_score'] = merged_df['leftover_amount'] * (6 - merged_df['rating'])
                    top3 = merged_df.drop_duplicates(subset=['food_item']) \
                        .sort_values(by='waste_score', ascending=False).head(3)
                    predicted_worst_food = top3[['food_item', 'meal', 'waste_score']].values.tolist()
                else:
                    predicted_worst_food = "No common food items found in waste and feedback data"
            else:
                predicted_worst_food = "Insufficient data for 14-day interval analysis"

            return render_template('mess/review_waste_feedback.html',
                                no_data=False,
                                floor_pie_plot=floor_pie_plot,
                                mess_waste_plot=mess_waste_plot,
                                plots=plots,
                                top_5_wasted_food=top5_waste_list,
                                predicted_worst_food=predicted_worst_food,
                                today=today.date())

    except Exception as e:
        print(f"Error: {e}")
        flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('mess_dashboard'))

