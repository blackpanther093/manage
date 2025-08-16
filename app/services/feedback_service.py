"""
Feedback-related services for ManageIt application
"""
import logging
from typing import List, Tuple, Dict
from app.models.database import DatabaseManager
from app.models.feedback_classifier import classify_feedback
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager
from app.utils.helpers import get_current_meal
class FeedbackService:
    """Service class for feedback operations"""
    
    CACHE_TTL = 86400  # 24 hours
    
    @classmethod
    def get_feedback_summary(cls, mess_name: str) -> List[Tuple]:
        """Fetch feedback summary with caching"""
        cache_key = f"feedback_summary_{mess_name}"
        # cache = cache_manager.get_cache('feedback_summary')
        # cached_data = cache.get(cache_key, cls.CACHE_TTL)
        cache = cache_manager.feedback_cache
        cached_data = cache.get(cache_key, cls.CACHE_TTL)

        if cached_data is not None:
            return cached_data
        
        dt = TimeUtils.get_fixed_time().date()
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT s.feedback_date, s.meal, COUNT(DISTINCT s.s_id) AS total_students, 
                           AVG(d.rating) AS avg_rating
                    FROM feedback_summary s
                    JOIN feedback_details d ON s.feedback_id = d.feedback_id
                    WHERE mess = %s and s.feedback_date >= %s - INTERVAL 30 DAY
                    GROUP BY s.feedback_date, s.meal
                    ORDER BY s.feedback_date DESC
                """, (mess_name, dt))
                feedback_summary_data = cursor.fetchall()

                cache.set(cache_key, feedback_summary_data)
                return feedback_summary_data

        except Exception as e:
            logging.error(f"Feedback summary error for mess {mess_name}: {e}")
            cache.set(cache_key, [])
            return []
    
    @classmethod
    def get_feedback_detail(cls, feedback_date: str, meal: str, mess_name: str) -> List[Tuple]:
        """Fetch feedback details with caching"""
        cache_key = f"feedback_detail_{feedback_date}_{meal}_{mess_name}"
        cache = cache_manager.feedback_cache
        cached_data = cache.get(cache_key, cls.CACHE_TTL)
        
        if cached_data is not None:
            return cached_data
        
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

                cache.set(cache_key, feedback_data)
                return feedback_data

        except Exception as e:
            logging.error(f"Error fetching feedback details for {cache_key}: {e}")
            cache.set(cache_key, [])
            return []
    
    @classmethod
    def submit_feedback(cls, student_id: str, feedback_date, meal: str, mess: str, 
                       food_ratings: Dict[str, int], comments: Dict[str, str]) -> bool:
        """Submit student feedback"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                # Insert feedback summary
                cursor.execute("""
                    INSERT INTO feedback_summary (s_id, feedback_date, meal, mess)
                    VALUES (%s, %s, %s, %s)
                """, (student_id, feedback_date, meal, mess))
                feedback_id = cursor.lastrowid
                
                # Insert feedback details
                for item, rating in food_ratings.items():
                    food_item = item[0] if isinstance(item, tuple) else item
                    cursor.execute("""
                        INSERT INTO feedback_details (feedback_id, food_item, rating, comments)
                        VALUES (%s, %s, %s, %s)
                    """, (feedback_id, food_item, rating, comments.get(item)))
                
                connection.commit()
                
                # Clear caches
                cls.clear_feedback_cache(mess)
                return True
                
        except Exception as e:
            logging.error(f"Feedback submission error: {e}")
            return False
    
    @classmethod
    def get_today_critical_feedbacks(cls) -> Tuple[List[Dict], List[Dict]]:
        """Get today's critical feedbacks for both messes"""
        meal = get_current_meal()
        mess1_critical = []
        mess2_critical = []

        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                today_date = TimeUtils.get_fixed_time().date()

                for mess, target_list in [('mess1', mess1_critical), ('mess2', mess2_critical)]:
                    cursor.execute("""
                        SELECT detail_id, d.feedback_id, food_item, rating, comments, created_at
                        FROM feedback_details d 
                        JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                        WHERE DATE(created_at) = %s AND s.mess = %s AND meal = %s
                        ORDER BY created_at ASC
                    """, (today_date, mess, meal))

                    rows = cursor.fetchall()

                    for row in rows:
                        text = (row.get('comments') or '').strip()
                        food_item = row.get('food_item') or ''
                        meal = row.get('meal') or ''
                        if text:
                            classification = classify_feedback(text)
                            if classification == "Critical":
                                # feedback_text = f"Meal: {meal}\tFood Item: {food_item}\tComment: {text}\n"
                                # target_list.append(feedback_text)
                                target_list.append({
                                    'comments': text,
                                    'food_item': food_item,
                                    'meal': meal
                                })

        except Exception as e:
            logging.error(f"Error fetching/classifying today's feedback: {e}")

        logging.info(f"Found {len(mess1_critical)} critical feedbacks for mess1 today.")
        logging.info(f"Found {len(mess2_critical)} critical feedbacks for mess2 today.")

        return mess1_critical, mess2_critical
    
    @classmethod
    def get_critical_feedback_texts_for_llm(cls) -> Dict[str, str]:
        """Get critical feedback texts organized by mess for LLM processing"""
        mess1_feedbacks, mess2_feedbacks = cls.get_today_critical_feedbacks()

        mess_wise_feedbacks = {
            "mess1": [],
            "mess2": []
        }

        for fb in mess1_feedbacks:
            comments = (fb.get('comments') or '').strip()
            if comments:
                mess_wise_feedbacks["mess1"].append(comments)

        for fb in mess2_feedbacks:
            comments = (fb.get('comments') or '').strip()
            if comments:
                mess_wise_feedbacks["mess2"].append(comments)

        combined_texts = {
            mess: "\n".join(comments) if comments else ""
            for mess, comments in mess_wise_feedbacks.items()
        }

        logging.info(f"Mess1 feedback (first 100 chars): {combined_texts['mess1'][:100]}...")
        logging.info(f"Mess2 feedback (first 100 chars): {combined_texts['mess2'][:100]}...")

        return combined_texts
    
    @classmethod
    def has_submitted_feedback(cls, student_id: str, date, meal: str, mess: str) -> bool:
        """Check if student has already submitted feedback"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT DISTINCT s_id FROM feedback_summary 
                    WHERE s_id = %s AND feedback_date = %s AND mess = %s AND meal = %s
                """, (student_id, date, mess, meal))
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Error checking feedback submission: {e}")
            return False
    
    @classmethod
    def clear_feedback_cache(cls, mess_name: str = None):
        """Clear feedback cache"""
        if mess_name:
            # Clear specific mess cache
            keys_to_clear = [key for key in cache_manager.feedback_cache._store.keys() 
                           if mess_name in key]
            for key in keys_to_clear:
                cache_manager.feedback_cache.clear(key)
        else:
            cache_manager.feedback_cache.clear()
