from apscheduler.schedulers.background import BackgroundScheduler
from app.models.database import DatabaseManager
from app.utils.helpers import get_fixed_time, create_admin_notification_from_critical_feedback, clear_notifications_cache
import logging
import pytz

def cleanup_old_menu():
    """Delete old menu and non-veg items once a day"""
    logging.info("Starting cleanup_old_menu job...")
    try:
        with DatabaseManager.get_db_cursor() as (cursor, connection):
            current_date = get_fixed_time().date()
            logging.info(f"Cleaning up data older than: {current_date}")

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
    logging.info("Starting generate_high_low_alerts job...")
    mess_list = ["mess1", "mess2"]

    for mess_name in mess_list:
        alerts = []
        logging.info(f"Processing alerts for {mess_name}...")
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = get_fixed_time().date()
                logging.info(f"Generated at: {created_at}")

                # High waste warnings
                floors = ['Ground', 'First'] if mess_name == 'mess1' else ['Second', 'Third']
                logging.info(f"Checking floors: {floors}")
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
                    logging.info(f"High waste recorded on {floor} Floor with {waste} Kg on {date}")

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
                    logging.info(f"Low feedback detected for {meal} on {date} with Avg. Rating {round(rating, 2)}")

            high_low_alerts_cache[mess_name] = alerts
            logging.info(f"✅ Alerts generated for {mess_name}: {len(alerts)} items")
        except Exception as e:
            logging.error(f"Error generating alerts for {mess_name}: {e}")

def send_admin_notification_job(app):
    """Scheduled job to generate and send separate admin notifications for each mess."""
    logging.info("Starting send_admin_notification_job...")
    with app.app_context():
        try:
            # Get dict with mess1 and mess2 summaries
            messages = create_admin_notification_from_critical_feedback()

            if not messages or not any(m.strip() for m in messages):
                logging.info("No critical feedback to notify today.")
                return

            logging.info(f"Sending {len(messages)} critical feedback notifications...")

            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = get_fixed_time()

                for message in messages:
                    cursor.execute("""
                        INSERT INTO notifications (message, recipient_type, created_at)
                        VALUES (%s, %s, %s)
                    """, (message, 'admin', created_at))

                connection.commit()

            clear_notifications_cache('admin')  # Clear cache for admin notifications
            logging.info("✅ Admin notifications sent and cache cleared.")

        except Exception as e:
            logging.error(f"Error sending admin notifications in scheduler: {e}")

def start_scheduler(app):
    ist = pytz.timezone("Asia/Kolkata")
    scheduler = BackgroundScheduler(timezone=ist)
    logging.info("Initializing BackgroundScheduler...")

    scheduler.add_job(func=cleanup_old_menu, trigger="cron", hour=0, minute=0)
    scheduler.add_job(func=generate_high_low_alerts, trigger="interval", minutes=60)

    meal_end_times = {
        "breakfast": (11, 0),
        "lunch": (16, 0),
        "snacks": (18, 30),
        "dinner": (0, 0),
    }

    for meal, (hour, minute) in meal_end_times.items():
        trigger_hour = hour
        trigger_minute = minute - 5
        if trigger_minute < 0:
            trigger_hour = (trigger_hour - 1) % 24
            trigger_minute += 60

        def job_wrapper(m=meal):
            logging.info(f"⏰ Running scheduled job for {m}")
            send_admin_notification_job(app)

        scheduler.add_job(
            func=job_wrapper,
            trigger="cron",
            hour=trigger_hour,
            minute=trigger_minute,
            id=f"notify_{meal}",
            timezone=ist,   # 🔹 ensure IST
        )

        logging.info(
            f"Scheduled admin notification for {meal} at {trigger_hour:02d}:{trigger_minute:02d} IST"
        )

    scheduler.start()
    logging.info("✅ Background scheduler started.")
    logging.info(f"Scheduled jobs: {scheduler.get_jobs()}")
