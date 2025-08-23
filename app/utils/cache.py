"""
Generic caching utilities for ManageIt application
"""
import threading
import time
from typing import Any, Optional, Dict, Tuple

class TTLCache:
    """Thread-safe TTL (Time To Live) cache implementation"""
    
    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str, ttl: float) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            value, timestamp = self._store.get(key, (None, 0))
            if time.time() - timestamp < ttl:
                return value
            # Remove expired entry
            self._store.pop(key, None)
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp"""
        with self._lock:
            self._store[key] = (value, time.time())
    
    def clear(self, key: Optional[str] = None) -> None:
        """Clear specific key or entire cache"""
        with self._lock:
            if key:
                self._store.pop(key, None)
            else:
                self._store.clear()
    
    def cleanup_expired(self, ttl: float) -> None:
        """Remove all expired entries"""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, timestamp) in self._store.items()
                if current_time - timestamp >= ttl
            ]
            for key in expired_keys:
                self._store.pop(key, None)

class CacheManager:
    """Centralized cache manager for the application"""
    
    def __init__(self):
        self.menu_cache = TTLCache()
        self.rating_cache = TTLCache()
        self.non_veg_cache = TTLCache()
        self.payment_cache = TTLCache()
        self.feedback_cache = TTLCache()
        self.waste_cache = TTLCache()
        self.notification_cache = TTLCache()
        self.feature_toggle_cache = TTLCache()
        self.poll_cache = TTLCache()

        # Cache TTL constants (in seconds)
        self.MENU_TTL = 3600  # 1 hour
        self.RATING_TTL = 1800  # 30 minutes
        self.PAYMENT_TTL = 3600  # 1 hour
        self.FEEDBACK_TTL = 86400  # 24 hours
        self.WASTE_TTL = 86400  # 24 hours
        self.NOTIFICATION_TTL = 1800  # 30 minutes
        self.FEATURE_TOGGLE_TTL = 86400  # 24 hours
        self.POLL_TTL = 3600  # 1 hour

    def clear_all_caches(self):
        """Clear all caches"""
        for cache in [self.menu_cache, self.rating_cache, self.non_veg_cache,
                     self.payment_cache, self.feedback_cache, self.waste_cache,
                     self.notification_cache, self.feature_toggle_cache, self.poll_cache]:
            cache.clear()

# Global cache manager instance
cache_manager = CacheManager()
