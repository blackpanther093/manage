"""
Rating-related services for ManageIt application
"""
import logging
from typing import Tuple, List
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class RatingService:
    """Service class for rating operations"""
    
    @classmethod
    def get_average_ratings(cls) -> Tuple[int, float, int, float]:
        """Get average ratings for both messes with caching"""
        meal = TimeUtils.get_current_meal()
        if not meal:
            return (0, 0.0, 0, 0.0)
        
        cache_key = f"avg_ratings_{meal}"
        
        # Try cache first
        cached_data = cache_manager.rating_cache.get(cache_key, cache_manager.RATING_TTL)
        if cached_data:
            return cached_data
        
        # Fetch from database
        try:
            ratings = cls._fetch_ratings_from_db(meal)
            cache_manager.rating_cache.set(cache_key, ratings)
            return ratings
        except Exception as e:
            logging.error(f"Error fetching average ratings: {e}")
            return (0, 0.0, 0, 0.0)
    
    @classmethod
    def _fetch_ratings_from_db(cls, meal: str) -> Tuple[int, float, int, float]:
        """Fetch ratings from database"""
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()
                results = {}

                for mess in ['mess1', 'mess2']:
                    # Average rating query
                    cursor.execute("""
                        SELECT AVG(rating) AS avg_rating
                        FROM feedback_details d
                        JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                        WHERE s.meal = %s AND s.mess = %s AND DATEDIFF(%s, s.feedback_date) % 14 = 0
                    """, (meal, mess, created_at))
                    avg = cursor.fetchone() or {"avg_rating": 0.0}

                    # Count query
                    cursor.execute("""
                        SELECT COUNT(*) AS count
                        FROM feedback_summary
                        WHERE meal = %s AND mess = %s AND DATEDIFF(%s, feedback_date) % 14 = 0
                    """, (meal, mess, created_at))
                    count = cursor.fetchone() or {"count": 0}

                    results[mess] = {
                        'avg_rating': round(avg['avg_rating'] or 0.0, 2),
                        'count': count['count'] or 0
                    }

                return (
                    results['mess1']['count'], results['mess1']['avg_rating'],
                    results['mess2']['count'], results['mess2']['avg_rating']
                )

        except Exception as e:
            logging.error(f"Error fetching ratings from database: {e}")
            return (0, 0.0, 0, 0.0)
    
    @classmethod
    def get_leaderboard(cls, mess_name: str, weekday: str, week_type: str) -> List[Tuple]:
        """Get food leaderboard with caching"""
        cache_key = f"leaderboard_{mess_name}_{weekday}_{week_type}"
        
        # Try cache first
        cached_data = cache_manager.rating_cache.get(cache_key, cache_manager.RATING_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT d.food_item, ROUND(AVG(d.rating), 2) as avg_rating
                    FROM feedback_details d
                    JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                    JOIN menu m ON d.food_item = m.food_item  
                    WHERE s.mess = %s AND m.day = %s AND m.week_type = %s
                    GROUP BY d.food_item
                    ORDER BY avg_rating DESC
                    LIMIT 5
                """, (mess_name, weekday, week_type))
                data = cursor.fetchall()
                
                cache_manager.rating_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Error fetching leaderboard: {e}")
            cache_manager.rating_cache.set(cache_key, [])
            return []
    
    @classmethod
    def get_monthly_average_ratings(cls) -> List[Tuple]:
        """Get monthly average ratings with caching"""
        cache_key = "monthly_avg_ratings"
        
        # Try cache first
        cached_data = cache_manager.rating_cache.get(cache_key, cache_manager.RATING_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().date()
                cursor.execute("""
                    SELECT s.mess, ROUND(AVG(d.rating), 2) as avg_rating
                    FROM feedback_details d
                    JOIN feedback_summary s ON d.feedback_id = s.feedback_id
                    WHERE d.created_at >= DATE_SUB(%s, INTERVAL 1 MONTH)
                    GROUP BY s.mess
                """, (created_at,))
                data = cursor.fetchall()
                
                cache_manager.rating_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Error fetching monthly avg ratings: {e}")
            cache_manager.rating_cache.set(cache_key, [])
            return []
    
    @classmethod
    def clear_rating_cache(cls):
        """Clear rating-related caches"""
        cache_manager.rating_cache.clear()
