"""
Enhanced security manager with comprehensive protection
"""
import time
import hashlib
import logging
import secrets
from typing import Dict, Optional, Tuple
from flask import request, session, g
from datetime import datetime, timedelta
import re

class SecurityManager:
    """Comprehensive security manager for the application"""
    
    def __init__(self):
        self.blocked_devices: Dict[str, float] = {}  # device_key -> block_time
        self.failed_attempts: Dict[str, Dict] = {}  # device_key -> attempt_data
        self.email_attempts: Dict[str, Dict] = {}  # email -> attempt_data
        self.session_tokens: Dict[str, Dict] = {}  # token -> session_data
        
        # Security patterns
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'expression\s*\(',
            r'vbscript:',
            r'data:text/html'
        ]
        
        # Rate limiting windows (in seconds)
        self.rate_windows = {
            'login': 300,      # 5 minutes
            'email': 3600,     # 1 hour
            'general': 60      # 1 minute
        }
        
        # Maximum attempts per window
        self.max_attempts = {
            'login': 5,
            'email': 3,
            'general': 20
        }

    def get_client_ip(self) -> str:
        """Get real client IP considering proxies"""
        # Check for forwarded IP headers (common in production)
        forwarded_ips = [
            request.headers.get('X-Forwarded-For'),
            request.headers.get('X-Real-IP'),
            request.headers.get('CF-Connecting-IP'),  # Cloudflare
            request.headers.get('X-Cluster-Client-IP')
        ]
        
        for ip_header in forwarded_ips:
            if ip_header:
                # Take the first IP if multiple are present
                ip = ip_header.split(',')[0].strip()
                if self._is_valid_ip(ip):
                    return ip
        
        return request.remote_addr or 'unknown'

    def get_device_fingerprint(self) -> str:
        """Generate device fingerprint from request headers"""
        user_agent = request.headers.get('User-Agent', '')
        accept_language = request.headers.get('Accept-Language', '')
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    def is_device_blocked(self, identifier: str = '') -> bool:
        """Check if specific device is currently blocked"""
        ip = self.get_client_ip()
        device_id = self.get_device_fingerprint()
        device_key = f"{identifier}:{ip}:{device_id}"
        
        if device_key in self.blocked_devices:
            if time.time() - self.blocked_devices[device_key] < 3600:  # 1 hour block
                return True
            else:
                # Clean expired block
                del self.blocked_devices[device_key]
        return False

    def record_failed_login(self, identifier: str) -> bool:
        """Record failed login attempt and return if device should be locked"""
        ip = self.get_client_ip()
        device_id = self.get_device_fingerprint()
        current_time = time.time()
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts = {
            k: v for k, v in self.failed_attempts.items()
            if current_time - v.get('last_attempt', 0) < 3600
        }
        
        # Record attempt with device-specific key
        key = f"{identifier}:{ip}:{device_id}"
        if key not in self.failed_attempts:
            self.failed_attempts[key] = {'count': 0, 'first_attempt': current_time}
        
        self.failed_attempts[key]['count'] += 1
        self.failed_attempts[key]['last_attempt'] = current_time
        
        # Block specific device after 5 failed attempts
        if self.failed_attempts[key]['count'] >= 5:
            self.blocked_devices[key] = current_time
            logging.warning(f"Device {device_id} from IP {ip} blocked due to multiple failed login attempts for {identifier}")
            return True
        
        return False

    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for successful login"""
        ip = self.get_client_ip()
        device_id = self.get_device_fingerprint()
        key = f"{identifier}:{ip}:{device_id}"
        self.failed_attempts.pop(key, None)
        self.blocked_devices.pop(key, None)  # Also clear any block

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False

    def rate_limit_email(self, email: str) -> bool:
        """Rate limit email sending"""
        current_time = time.time()
        window = self.rate_windows['email']
        max_attempts = self.max_attempts['email']
        
        # Clean old attempts
        self.email_attempts = {
            k: v for k, v in self.email_attempts.items()
            if current_time - v['first_attempt'] < window
        }
        
        if email not in self.email_attempts:
            self.email_attempts[email] = {
                'count': 1,
                'first_attempt': current_time,
                'last_attempt': current_time
            }
            return False
        
        attempt_data = self.email_attempts[email]
        
        # Check if within rate limit window
        if current_time - attempt_data['first_attempt'] < window:
            if attempt_data['count'] >= max_attempts:
                logging.warning(f"Email rate limit exceeded for {email}")
                return True
            
            attempt_data['count'] += 1
            attempt_data['last_attempt'] = current_time
        else:
            # Reset counter for new window
            self.email_attempts[email] = {
                'count': 1,
                'first_attempt': current_time,
                'last_attempt': current_time
            }
        
        return False

    def validate_input(self, input_data: str, input_type: str = 'general') -> Tuple[bool, str]:
        """Validate input for security threats"""
        if not input_data:
            return True, "Valid"
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                logging.warning(f"Suspicious pattern detected: {pattern} in input from IP {self.get_client_ip()}")
                return False, f"Suspicious pattern detected"
        
        # Input type specific validation
        if input_type == 'email':
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, input_data):
                return False, "Invalid email format"
        
        elif input_type == 'password':
            if len(input_data) < 8:
                return False, "Password too short"
            if not re.search(r'[A-Z]', input_data):
                return False, "Password must contain uppercase letter"
            if not re.search(r'[a-z]', input_data):
                return False, "Password must contain lowercase letter"
            if not re.search(r'\d', input_data):
                return False, "Password must contain number"
        
        return True, "Valid"

    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)

    def create_session(self, user_id: str, role: str, additional_data: Dict = None) -> str:
        """Create secure session with token"""
        token = self.generate_session_token()
        session_data = {
            'user_id': user_id,
            'role': role,
            'created_at': time.time(),
            'ip': self.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:100],
            'last_activity': time.time()
        }
        
        if additional_data:
            session_data.update(additional_data)
        
        self.session_tokens[token] = session_data
        session['security_token'] = token
        
        return token

    def validate_session(self) -> bool:
        """Validate current session security"""
        token = session.get('security_token')
        if not token or token not in self.session_tokens:
            return False
        
        session_data = self.session_tokens[token]
        current_time = time.time()
        
        # Check session timeout (24 hours)
        if current_time - session_data['created_at'] > 86400:
            self.invalidate_session(token)
            return False
        
        # Check inactivity timeout (2 hours)
        if current_time - session_data['last_activity'] > 7200:
            self.invalidate_session(token)
            return False
        
        # Validate IP consistency (optional - can be disabled for mobile users)
        current_ip = self.get_client_ip()
        if session_data['ip'] != current_ip:
            logging.warning(f"IP change detected for session {token}: {session_data['ip']} -> {current_ip}")
            # Don't invalidate automatically - just log for monitoring
        
        # Update last activity
        session_data['last_activity'] = current_time
        
        return True

    def invalidate_session(self, token: str = None):
        """Invalidate session token"""
        if not token:
            token = session.get('security_token')
        
        if token and token in self.session_tokens:
            del self.session_tokens[token]
        
        session.pop('security_token', None)

    def cleanup_expired_data(self):
        """Clean up expired security data"""
        current_time = time.time()
        
        # Clean expired blocks (older than 1 hour)
        self.blocked_devices = {
            k: v for k, v in self.blocked_devices.items()
            if current_time - v < 3600
        }
        
        # Clean expired failed attempts (older than 1 hour)
        self.failed_attempts = {
            k: v for k, v in self.failed_attempts.items()
            if current_time - v.get('last_attempt', 0) < 3600
        }
        
        # Clean expired email attempts (older than 1 hour)
        self.email_attempts = {
            k: v for k, v in self.email_attempts.items()
            if current_time - v['first_attempt'] < 3600
        }
        
        # Clean expired sessions (older than 24 hours)
        self.session_tokens = {
            k: v for k, v in self.session_tokens.items()
            if current_time - v['created_at'] < 86400
        }

    def get_security_stats(self) -> Dict:
        """Get current security statistics"""
        return {
            'blocked_devices': len(self.blocked_devices),
            'failed_attempts': len(self.failed_attempts),
            'email_rate_limits': len(self.email_attempts),
            'active_sessions': len(self.session_tokens)
        }

# Global security manager instance
security_manager = SecurityManager()
