"""
Legacy helper functions for backward compatibility
Import from service classes for new code
"""
from app.utils.time_utils import TimeUtils
from app.services.menu_service import MenuService
from app.services.rating_service import RatingService
from app.services.payment_service import PaymentService
from app.services.feedback_service import FeedbackService
from app.services.waste_service import WasteService
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.services.llm_service import LLMService

# Time utilities
get_fixed_time = TimeUtils.get_fixed_time
seconds_until_next_meal = TimeUtils.seconds_until_next_meal
is_odd_week = TimeUtils.is_odd_week
get_current_meal = TimeUtils.get_current_meal

# Menu services
get_menu = MenuService.get_menu
get_non_veg_menu = MenuService.get_non_veg_menu
clear_menu_cache = MenuService.clear_menu_cache
get_amount_data = MenuService.get_amount_data

# Rating services
avg_rating = RatingService.get_average_ratings
get_leaderboard_cached = RatingService.get_leaderboard
get_monthly_avg_ratings_cached = RatingService.get_monthly_average_ratings

# Payment services
get_payment_summary = PaymentService.get_payment_summary
clear_payment_summary_cache = PaymentService.clear_payment_cache

# Feedback services
get_feedback_summary = FeedbackService.get_feedback_summary
get_feedback_detail = FeedbackService.get_feedback_detail
clear_feedback_summary_cache = FeedbackService.clear_feedback_cache
clear_feedback_detail_cache = FeedbackService.clear_feedback_cache
get_today_critical_feedbacks = FeedbackService.get_today_critical_feedbacks
get_critical_feedback_texts_for_llm = FeedbackService.get_critical_feedback_texts_for_llm

# Waste services
get_waste_summary = WasteService.get_waste_summary
get_waste_feedback = WasteService.get_waste_feedback_data
clear_waste_feedback_cache = WasteService.clear_waste_cache
clear_waste_summary_cache = WasteService.clear_waste_cache

# Notification services
get_notifications = NotificationService.get_notifications
clear_notifications_cache = NotificationService.clear_notifications_cache
get_feature_toggle_status = NotificationService.get_feature_toggle_status
clear_feature_toggle_cache = NotificationService.clear_feature_toggle_cache
get_switch_activity = NotificationService.get_switch_activity
clear_switch_activity_cache = NotificationService.clear_notifications_cache

# Email services
send_confirmation_email = EmailService.send_confirmation_email

# LLM services
call_your_llm = LLMService.call_llm
summarize_feedback_text = LLMService.summarize_feedback_text
create_admin_notification_from_critical_feedback = LLMService.create_admin_notification_from_critical_feedback

# Cache management
def clear_non_veg_menu_cache(mess_name, date=None, meal=None):
    """Legacy function for clearing non-veg menu cache"""
    MenuService.clear_menu_cache()

def clear_amount_data_cache(food_item=None, mess_name=None, date=None, meal=None):
    """Legacy function for clearing amount data cache"""
    PaymentService.clear_payment_cache()
