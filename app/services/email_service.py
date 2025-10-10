"""
Email-related services for ManageIt application
"""
# CHANGED: Replaced smtplib with sendgrid and os
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
# ---
from flask import current_app, url_for
import logging
from app.utils.security import security_manager

class EmailService:
    """Service class for email operations"""

    @staticmethod
    def _get_brevo_api_client():
        """Helper method to initialize and return the Brevo API client."""
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY')
        return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
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
        """Send account confirmation email with token link using Brevo."""
        if security_manager.rate_limit_email(recipient_email):
            logging.warning(f"Email rate limit exceeded for {recipient_email}")
            return False

        try:
            sender_email = os.environ.get('SENDER_EMAIL')
            if not os.environ.get('BREVO_API_KEY') or not sender_email:
                logging.error("BREVO_API_KEY or SENDER_EMAIL environment variables not set.")
                return False

            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            subject = "Confirm your ManageIt account"
            # Using HTML content to make the link clickable
            html_content = f"""
            <div style="font-family: sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #0052cc;">Welcome to ManageIt!</h2>
                <p>Thanks for signing up. Please click the button below to activate your account.</p>
                <a href="{confirm_url}" style="display: inline-block; padding: 12px 24px; margin: 20px 0; font-size: 16px; color: #fff; background-color: #0065ff; text-decoration: none; border-radius: 5px;">
                    Confirm Your Email
                </a>
                <p>For your security, this link will expire in 15 minutes.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #777;">If you're having trouble with the button, copy and paste this URL into your browser:<br>{confirm_url}</p>
            </div>
            """

            sender = {"name": "ManageIt Team", "email": sender_email}
            to = [{"email": recipient_email}]
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to, 
                sender=sender, 
                subject=subject, 
                html_content=html_content
            )

            api_instance = cls._get_brevo_api_client()
            api_instance.send_transac_email(send_smtp_email)
            
            security_manager.record_email_sent(recipient_email)
            logging.info(f"Confirmation email sent successfully to {security_manager.hash_sensitive_data(recipient_email)}")
            return True

        except ApiException as e:
            logging.error(f"Failed to send Brevo confirmation email: {e.body}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return False

    @classmethod
    def send_password_reset_email(cls, recipient_email: str, token: str) -> bool:
        """Send password reset email using Brevo."""
        if security_manager.rate_limit_email(recipient_email):
            logging.warning(f"Email rate limit exceeded for {recipient_email}")
            return False

        try:
            sender_email = os.environ.get('SENDER_EMAIL')
            if not os.environ.get('BREVO_API_KEY') or not sender_email:
                logging.error("BREVO_API_KEY or SENDER_EMAIL environment variables not set.")
                return False

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            subject = "Reset your ManageIt password"
            html_content = f"""
            <div style="font-family: sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #0052cc;">Password Reset Request</h2>
                <p>We received a request to reset the password for your ManageIt account. Please click the button below to proceed.</p>
                <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; margin: 20px 0; font-size: 16px; color: #fff; background-color: #0065ff; text-decoration: none; border-radius: 5px;">
                    Reset Your Password
                </a>
                <p>For your security, this link will expire in 15 minutes.</p>
                <p>If you didn't request this, please ignore this email and your password will remain unchanged.</p>
                <hr style="border: none; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #777;">If you're having trouble with the button, copy and paste this URL into your browser:<br>{reset_url}</p>
            </div>
            """

            sender = {"name": "ManageIt Team", "email": sender_email}
            to = [{"email": recipient_email}]

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to, 
                sender=sender, 
                subject=subject, 
                html_content=html_content
            )

            api_instance = cls._get_brevo_api_client()
            api_instance.send_transac_email(send_smtp_email)
            
            security_manager.record_email_sent(recipient_email)
            logging.info(f"Password reset email sent successfully to {security_manager.hash_sensitive_data(recipient_email)}")
            return True

        except ApiException as e:
            logging.error(f"Failed to send Brevo password reset email: {e.body}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return False