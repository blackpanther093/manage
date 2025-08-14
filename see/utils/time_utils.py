"""
Time-related utility functions for ManageIt application
"""
from datetime import datetime, timezone
import pytz

class TimeUtils:
    """Utility class for time operations"""
    
    IST_TIMEZONE = pytz.timezone("Asia/Kolkata")
    
    @classmethod
    def get_fixed_time(cls):
        """Get current time in IST timezone"""
        utc_now = datetime.now(timezone.utc)
        return utc_now.astimezone(cls.IST_TIMEZONE)
    
    @classmethod
    def seconds_until_next_meal(cls):
        """Calculate seconds until next meal boundary"""
        now = cls.get_fixed_time()
        hour = now.hour
        minute = now.minute
        total_minutes = hour * 60 + minute

        # Meal boundaries in minutes
        boundaries = [
            0,          # Breakfast start
            11 * 60,    # Lunch start
            16 * 60,    # Snacks start
            18 * 60 + 30, # Dinner start
            24 * 60     # End of day
        ]

        for b in boundaries:
            if b > total_minutes:
                return (b - total_minutes) * 60  # seconds until next boundary
        
        # If somehow no boundary found (e.g. at end of day), return 1 hour as fallback
        return 3600
    
    @classmethod
    def is_odd_week(cls, date=None):
        """Determine if the given date falls in an odd or even week"""
        if date is None:
            date = cls.get_fixed_time().date()
        
        start_date = datetime(2025, 7, 27).date()
        days_difference = (date - start_date).days
        return (days_difference // 7) % 2 == 0
    
    @classmethod
    def get_current_meal(cls, hour=None):
        """Get current meal based on time"""
        if hour is None:
            hour = cls.get_fixed_time().hour
            minute = cls.get_fixed_time().minute
            total_time = hour * 60 + minute
        else:
            total_time = hour * 60
        
        if 0 <= total_time < 11*60:
            return "Breakfast"
        elif 11*60 <= total_time < 16*60:
            return "Lunch"
        elif 16*60 <= total_time <= 18*60 + 30:
            return "Snacks"
        elif 18*60 + 30 < total_time <= 23*60 + 59:
            return "Dinner"
        return None
