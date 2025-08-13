"""
Security utilities for ManageIt application
"""
import hashlib
import secrets
import time
from typing import Dict, Optional
from flask import request, session
import logging

class SecurityManager:
    """Security management utilities"""
    
    def __init__(self):
        self.failed_attempts: Dict[str, Dict] = {}
        self.blocked_ips: Dict[str, float] = {}
        self.email_attempts: Dict[str, Dict] = {}
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        if request.environ.get('HTTP_X_FORWARDED_FOR'):
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        elif request.environ.get('HTTP_X_REAL_IP'):
            return request.environ['HTTP_X_REAL_IP']
        else:
            return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        if ip in self.blocked_ips:
            if time.time() - self.blocked_ips[ip] < 3600:  # 1 hour block
                return True
            else:
                del self.blocked_ips[ip]
        return False
    
    def record_failed_login(self, identifier: str) -> bool:
        """Record failed login attempt and return if account should be locked"""
        ip = self.get_client_ip()
        current_time = time.time()
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts = {
            k: v for k, v in self.failed_attempts.items()
            if current_time - v.get('last_attempt', 0) < 3600
        }
        
        # Record attempt
        key = f"{identifier}:{ip}"
        if key not in self.failed_attempts:
            self.failed_attempts[key] = {'count': 0, 'first_attempt': current_time}
        
        self.failed_attempts[key]['count'] += 1
        self.failed_attempts[key]['last_attempt'] = current_time
        
        # Block after 5 failed attempts
        if self.failed_attempts[key]['count'] >= 5:
            self.blocked_ips[ip] = current_time
            logging.warning(f"IP {ip} blocked due to multiple failed login attempts for {identifier}")
            return True
        
        return False
    
    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for successful login"""
        ip = self.get_client_ip()
        key = f"{identifier}:{ip}"
        self.failed_attempts.pop(key, None)
    
    def can_send_email(self, email: str) -> bool:
        """Check if email can be sent (rate limiting)"""
        current_time = time.time()
        
        # Clean old attempts
        self.email_attempts = {
            k: v for k, v in self.email_attempts.items()
            if current_time - v.get('last_sent', 0) < 3600
        }
        
        if email not in self.email_attempts:
            self.email_attempts[email] = {'count': 0, 'last_sent': 0}
        
        # Allow max 3 emails per hour
        if self.email_attempts[email]['count'] >= 3:
            if current_time - self.email_attempts[email]['last_sent'] < 3600:
                return False
            else:
                self.email_attempts[email] = {'count': 0, 'last_sent': 0}
        
        return True
    
    def record_email_sent(self, email: str):
        """Record email sent"""
        current_time = time.time()
        if email not in self.email_attempts:
            self.email_attempts[email] = {'count': 0, 'last_sent': 0}
        
        self.email_attempts[email]['count'] += 1
        self.email_attempts[email]['last_sent'] = current_time
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    def validate_session(self) -> bool:
        """Validate current session"""
        if 'role' not in session:
            return False
        
        # Check session timeout (4 hours)
        if 'last_activity' in session:
            if time.time() - session['last_activity'] > 14400:  # 4 hours
                session.clear()
                return False
        
        # Update last activity
        session['last_activity'] = time.time()
        return True
    
    def secure_session_data(self):
        """Add security data to session"""
        session['csrf_token'] = self.generate_secure_token(16)
        session['last_activity'] = time.time()
        session['ip_hash'] = hashlib.sha256(self.get_client_ip().encode()).hexdigest()

# Global security manager instance
security_manager = SecurityManager()
