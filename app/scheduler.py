from apscheduler.schedulers.background import BackgroundScheduler
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time
import logging

def cleanup_old_menu():
    """Delete old menu and non-veg items once a day"""
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            current_date = get_fixed_time().date()

            cursor.execute("DELETE FROM temporary_menu WHERE created_at < %s", (current_date,))
            cursor.execute("""
                DELETE FROM non_veg_menu_items 
                WHERE menu_id IN (
                    SELECT menu_id FROM non_veg_menu_main 
                    WHERE menu_date < %s
                )
            """, (current_date,))
            cursor.execute("DELETE FROM non_veg_menu_main WHERE menu_date < %s", (current_date,))
            connection.commit()

        logging.info("✅ Old menu data cleaned")
    except Exception as e:
        logging.error(f"Error cleaning old menu data: {e}")

high_low_alerts_cache = {}  # { "mess1": [...], "mess2": [...] }

def generate_high_low_alerts():
    """Generate high waste and low feedback alerts for each mess."""
    mess_list = ["mess1", "mess2"]

    for mess_name in mess_list:
        alerts = []
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = get_fixed_time().date()

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
                    alerts.append(
                        (f"⚠️ High waste recorded on {floor} Floor with {waste} Kg.", date)
                    )

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
                    alerts.append(
                        (f"❗ Low feedback detected for {meal} on {date} "
                         f"with Avg. Rating {round(rating, 2)}", date)
                    )

            high_low_alerts_cache[mess_name] = alerts
            logging.info(f"✅ Alerts generated for {mess_name}: {len(alerts)} items")
        except Exception as e:
            logging.error(f"Error generating alerts for {mess_name}: {e}")

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=cleanup_old_menu, trigger="cron", hour=0, minute=0)  # midnight daily
    scheduler.add_job(func=generate_high_low_alerts, trigger="interval", minutes=60)  # update alerts every 30 mins
    scheduler.start()
    app.logger.info("Background scheduler started")
