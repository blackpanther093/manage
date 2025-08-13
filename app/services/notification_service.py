"""
Notification-related services for ManageIt application
"""
import logging
from typing import List, Tuple, Optional, Dict
from app.models.database import DatabaseManager
from app.utils.time_utils import TimeUtils
from app.utils.cache import cache_manager

class NotificationService:
    """Service class for notification operations"""
    
    @classmethod
    def get_notifications(cls, recipient_type: str) -> List[Tuple]:
        """Get notifications with caching"""
        cache_key = f"notifications_{recipient_type}"
        
        # Try cache first
        cached_data = cache_manager.notification_cache.get(cache_key, cache_manager.NOTIFICATION_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                cursor.execute("""
                    SELECT message, created_at 
                    FROM notifications 
                    WHERE recipient_type = %s
                    AND created_at >= NOW() - INTERVAL 7 DAY 
                    ORDER BY created_at DESC
                """, (recipient_type,))
                data = cursor.fetchall()

                cache_manager.notification_cache.set(cache_key, data)
                return data
                
        except Exception as e:
            logging.error(f"Error fetching {recipient_type} notifications: {e}")
            cache_manager.notification_cache.set(cache_key, [])
            return []
    
    @classmethod
    def send_notification(cls, message: str, recipient_type: str) -> bool:
        """Send notification"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = TimeUtils.get_fixed_time()
                cursor.execute("""
                    INSERT INTO notifications (message, recipient_type, created_at)
                    VALUES (%s, %s, %s)
                """, (message, recipient_type, created_at))
                connection.commit()
                
                # Clear cache
                cls.clear_notifications_cache(recipient_type)
                return True
                
        except Exception as e:
            logging.error(f"Send notification error: {e}")
            return False
    
    @classmethod
    def get_feature_toggle_status(cls) -> Optional[Dict]:
        """Get feature toggle status with caching"""
        cache_key = "feature_toggle"
        
        # Try cache first
        cached_data = cache_manager.feature_toggle_cache.get(cache_key, cache_manager.FEATURE_TOGGLE_TTL)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        try:
            with DatabaseManager.get_db_cursor(dictionary=True) as (cursor, connection):
                cursor.execute("SELECT enabled_at, disabled_at FROM feature_toggle LIMIT 1")
                toggle = cursor.fetchone()
                
                cache_manager.feature_toggle_cache.set(cache_key, toggle)
                return toggle
                
        except Exception as e:
            logging.error(f"Error fetching feature toggle status: {e}")
            cache_manager.feature_toggle_cache.set(cache_key, None)
            return None
    
    @classmethod
    def update_feature_toggle(cls, is_enabled: bool) -> bool:
        """Update feature toggle status"""
        try:
            with DatabaseManager.get_db_cursor() as (cursor, connection):
                created_at = TimeUtils.get_fixed_time().strftime('%Y-%m-%d %H:%M:%S')
                
                if is_enabled:
                    cursor.execute("""
                        UPDATE feature_toggle
                        SET is_enabled = TRUE, enabled_at = %s, disabled_at = NULL
                    """, (created_at,))
                else:
                    cursor.execute("""
                        UPDATE feature_toggle
                        SET is_enabled = FALSE, disabled_at = %s, enabled_at = NULL
                    """, (created_at,))
                
                connection.commit()
                
                # Clear cache
                cls.clear_feature_toggle_cache()
                return True
                
        except Exception as e:
            logging.error(f"Feature toggle update error: {e}")
            return False
    
    @classmethod
    def get_switch_activity(cls, mess_name: str) -> Tuple[List[Dict], List[Dict]]:
        """Get mess switch activity with caching"""
        cache_key = f"switch_activity_{mess_name}"
        
        # Try cache first
        cached_data = cache_manager.notification_cache.get(cache_key, cache_manager.NOTIFICATION_TTL)
        if cached_data is not None:
            return cached_data
        
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

            result = (joined_students, left_students)
            cache_manager.notification_cache.set(cache_key, result)
            return result

        except Exception as e:
            logging.error(f"Switch activity error: {e}")
            return [], []
    
    @classmethod
    def clear_notifications_cache(cls, recipient_type: str = None):
        """Clear notification cache"""
        if recipient_type:
            cache_key = f"notifications_{recipient_type}"
            cache_manager.notification_cache.clear(cache_key)
        else:
            cache_manager.notification_cache.clear()
    
    @classmethod
    def clear_feature_toggle_cache(cls):
        """Clear feature toggle cache"""
        cache_manager.feature_toggle_cache.clear("feature_toggle")
