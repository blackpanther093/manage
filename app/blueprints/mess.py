"""
Mess official routes for ManageIt application
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, get_current_meal, get_menu, is_odd_week, get_notifications, clear_non_veg_menu_cache, get_non_veg_menu, get_amount_data, get_payment_summary, clear_payment_summary_cache, get_waste_feedback, clear_waste_feedback_cache, get_switch_activity, clear_waste_summary_cache
from app.scheduler import high_low_alerts_cache
from app.services.waste_service import WasteService
from app.services.payment_service import PaymentService  # Make sure this is imported
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
    meal, _ = get_menu()
    
    if not meal:
        flash("No meal available at the moment.", 'error')
        return redirect(url_for('main.home'))
    
    previous_items = []
    created_at = get_fixed_time().date()      

    if request.method == 'POST':
        food_items = request.form.getlist('food_item[]')
        costs = request.form.getlist('cost[]')
        
        # Clean input
        food_items = [item.strip() for item in food_items if item.strip()]
        costs = [c.strip() for c in costs if c.strip()]
        
        if not food_items or not costs or len(food_items) != len(costs):
            flash("Invalid input. Ensure all fields are filled.", 'error')
            return redirect(url_for('mess.add_non_veg_menu'))
        
        # created_at = get_fixed_time().date()
        existing_items = get_non_veg_menu(mess, created_at, meal)
        print(f"Existing items for {mess} on {created_at} ({meal}): {existing_items}")
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                # created_at = get_fixed_time().date()
                # existing_items = get_non_veg_menu(mess, created_at, meal)
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
                
                clear_non_veg_menu_cache(mess)

        except Exception as e:
            logging.error(f"Add non-veg menu error: {e}")
            flash("An error occurred while adding the menu.", 'error')
        
        return redirect(url_for('mess.add_non_veg_menu'))
    
    # Load previous items
    previous_items = get_non_veg_menu(mess, created_at, meal)
    print(f"Previous items for {mess} on {created_at} ({meal}): {previous_items}")
    
    return render_template('mess/add_non_veg_menu.html', 
                         meal=meal, 
                         mess=mess, 
                         previous_items=previous_items)

@mess_bp.route('/delete-item', methods=['POST'])
def delete_item():
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response

    mess = session.get('mess')
    food_item = request.form.get('food_item')
    created_at = get_fixed_time().date()
    meal = get_current_meal()

    if not food_item:
        flash("Error: Item not found", 'error')
        return redirect(url_for('mess.add_non_veg_menu'))

    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                DELETE FROM non_veg_menu_items 
                WHERE menu_id in (
                    SELECT menu_id FROM non_veg_menu_main
                    WHERE menu_date = %s AND meal = %s AND mess = %s
                )
                AND food_item = %s
            """, (created_at, meal, mess, food_item))
            connection.commit()
            flash('Item deleted successfully!', 'success')

            clear_non_veg_menu_cache(mess)

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
    meal, veg_menu_items = get_menu()
    non_veg_menu1 = get_non_veg_menu("mess1")
    non_veg_menu2 = get_non_veg_menu("mess2")

    if ((meal == 'Breakfast' and current_hour < 9) or 
        (meal == 'Lunch' and current_hour < 14) or 
        (meal == 'Snacks' and current_hour < 18) or 
        (meal == 'Dinner' and current_hour < 21)):
        meal = None
    
    if not meal:
        flash("No meal available at the moment.", 'error')
        return redirect(url_for('mess.dashboard'))
    
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
        
        created_at = get_fixed_time().date()

        # ✅ Use WasteService instead of manual DB code
        success = WasteService.submit_waste_data(
            waste_date=created_at,
            meal=meal,
            floor=floor,
            total_waste=waste_amount,
            prepared_amounts=prepared_amounts,
            leftover_amounts=leftover_amounts
        )

        if success:
            flash("Waste data submitted successfully!", 'success')
            # clear_waste_feedback_cache(mess)
            # clear_waste_summary_cache()
            return redirect(url_for('mess.dashboard'))
        else:
            flash("Waste data already submitted for today or an error occurred.", 'error')
            return redirect(url_for('mess.dashboard'))
    
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
        
        # Get food item cost
        amount_data = get_amount_data(food_item, mess_name, created_at, meal)
        
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Validate student
                cursor.execute("SELECT mess FROM student WHERE s_id = %s", (s_id,))
                student_data = cursor.fetchone()
                
                if not student_data or student_data[0] != mess_name:
                    flash("Invalid student ID or student not from your mess.", "error")
                    return redirect(url_for('mess.add_payment'))
                
                if not amount_data:
                    flash("Invalid food item selected.", "error")
                    return redirect(url_for('mess.add_payment'))
                
                item_id, amount = amount_data

            # ✅ Use PaymentService to insert payment
            success = PaymentService.add_payment(
                s_id=s_id,
                mess=mess_name,
                meal=meal,
                payment_date=created_at,
                food_item=food_item,
                amount=amount,
                payment_mode=payment_mode,
                item_id=item_id
            )

            if success:
                flash("Payment details entered successfully!", "success")
                # clear_payment_summary_cache(mess_name)
            # else:
            #     flash("An error occurred while adding the payment.", "error")

        except Exception as e:
            logging.error(f"Add payment error: {e}")
            flash("An error occurred while adding the payment.", "error")
        
        return redirect(url_for('mess.add_payment'))
    
    # Get available food items
    food_items = get_non_veg_menu(mess_name)
    
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
    summary_data = get_payment_summary(mess_name)
    
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
    joined_students, left_students = get_switch_activity(mess_name)
    
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
    notifications = get_notifications('mess_official')
    
    # Append precomputed high/low alerts
    alerts = high_low_alerts_cache.get(mess_name, [])
    notifications.extend(alerts)

    return render_template("notifications.html", 
                         notifications=notifications, 
                         back_url='/mess/dashboard')

@mess_bp.route('/review-waste-feedback')
def review_waste_feedback():
    redirect_response = require_mess_login()
    if redirect_response:
        return redirect_response
    
    mess_name = session['mess']

    waste_data, feedback_data = get_waste_feedback(mess_name)

    if not waste_data or not feedback_data:
        return render_template('mess/review_waste_feedback.html', no_data=True)
    
    try:
        with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):

            current_meal = get_current_meal()

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

