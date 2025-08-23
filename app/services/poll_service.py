import logging
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class PollService:
    """Service class for poll stats operations"""
    
    CACHE_TTL = cache_manager.POLL_TTL  # 1 hour

    @classmethod
    def get_poll_stats(cls, meal: str) -> dict:
        """Get poll stats with caching, similar to RatingService"""
        if not meal:
            return {"mess1": {"Like": 0, "Dislike": 0}, 
                    "mess2": {"Like": 0, "Dislike": 0}}

        poll_date = TimeUtils.get_fixed_time().date()
        cache_key = f"poll_stats_{poll_date}_{meal}"

        # Use cache properly with TTL
        cached_data = cache_manager.poll_cache.get(cache_key, cls.CACHE_TTL)
        if cached_data:
            return cached_data

        # Fetch from DB
        try:
            stats = cls._fetch_poll_stats_from_db(meal, poll_date)
            cache_manager.poll_cache.set(cache_key, stats)
            return stats
        except Exception as e:
            logging.error(f"Error fetching poll stats: {e}")
            return {"mess1": {"Like": 0, "Dislike": 0}, 
                    "mess2": {"Like": 0, "Dislike": 0}}

    @classmethod
    def _fetch_poll_stats_from_db(cls, meal: str, poll_date):
        """Fetch poll stats from database"""
        poll_stats = {"mess1": {"Like": 0, "Dislike": 0}, 
                      "mess2": {"Like": 0, "Dislike": 0}}

        with DatabaseManager.get_db_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT mess, vote, COUNT(*) as count
                FROM meal_poll
                WHERE poll_date = %s AND meal = %s
                GROUP BY mess, vote
            """, (poll_date, meal))
            rows = cursor.fetchall()

            for mess, vote, count in rows:
                if mess in poll_stats and vote in poll_stats[mess]:
                    poll_stats[mess][vote] = count

        return poll_stats

    @classmethod
    def clear_poll_cache(cls, meal: str):
        """Clear poll stats cache for a given meal (call this after someone votes)"""
        poll_date = TimeUtils.get_fixed_time().date()
        cache_key = f"poll_stats_{poll_date}_{meal}"
        cache_manager.poll_cache.clear(cache_key)
