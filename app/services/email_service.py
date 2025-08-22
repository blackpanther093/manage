"""
Email-related services for ManageIt application
"""
import smtplib
from email.mime.text import MIMEText
from flask import current_app, url_for
import logging
from app.utils.security import security_manager

class EmailService:
    """Service class for email operations"""
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email to prevent duplicates (e.g., + trick, dots)"""
        email = email.strip().lower()
        if '@' not in email:
            return email  # fallback for invalid email

        local_part, domain = email.split('@')

        # If domain is Gmail, Googlemail, or institute domain (hosted on Gmail)
        if domain in ['gmail.com', 'googlemail.com', 'iiitdm.ac.in']:
            local_part = local_part.split('+')[0]  # remove +tag
            local_part = local_part.replace('.', '')  # remove dots

        return f"{local_part}@{domain}"
    
    @classmethod
    def send_confirmation_email(cls, recipient_email: str, token: str) -> bool:
        """Send account confirmation email with token link"""
        # Check rate limiting
        # if not security_manager.can_send_email(recipient_email):
        if security_manager.rate_limit_email(recipient_email):
            logging.warning(f"Email rate limit exceeded for {recipient_email}")
            return False
        
        try:
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            subject = "Confirm your ManageIt account"
            body = f"""Hi,

Click the link below to confirm your account:
{confirm_url}

This link will expire in 15 minutes for security reasons.

If you didn't request this, please ignore this email.

Best regards,
ManageIt Team"""

            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
            msg['To'] = recipient_email

            with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
                if current_app.config['MAIL_USE_TLS']:
                    server.starttls()
                server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            # Record email sent
            security_manager.record_email_sent(recipient_email)
            logging.info(f"Confirmation email sent successfully to {security_manager.hash_sensitive_data(recipient_email)}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send confirmation email: {e}")
            return False
    
    @classmethod
    def send_password_reset_email(cls, recipient_email: str, token: str) -> bool:
        """Send password reset email"""
        # Check rate limiting
        # if not security_manager.can_send_email(recipient_email):
        if security_manager.rate_limit_email(recipient_email):
            logging.warning(f"Email rate limit exceeded for {recipient_email}")
            return False
        
        try:
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            subject = "Reset your ManageIt password"
            body = f"""Hi,

You requested a password reset for your ManageIt account.

Click the link below to reset your password:
{reset_url}

This link will expire in 15 minutes for security reasons.

If you didn't request this, please ignore this email and your password will remain unchanged.

Best regards,
ManageIt Team"""

            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
            msg['To'] = recipient_email

            with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
                if current_app.config['MAIL_USE_TLS']:
                    server.starttls()
                server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            # Record email sent
            security_manager.record_email_sent(recipient_email)
            logging.info(f"Password reset email sent successfully to {security_manager.hash_sensitive_data(recipient_email)}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send password reset email: {e}")
            return False
