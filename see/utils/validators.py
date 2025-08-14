"""
Input validation utilities for ManageIt application
"""
import re
from typing import Optional, List, Dict, Any
from flask import request
import bleach
from werkzeug.datastructures import FileStorage

class ValidationError(Exception):
    """Custom validation error"""
    pass

class InputValidator:
    """Comprehensive input validation class"""
    
    # Regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    STUDENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9]{6,20}$')
    PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$')
    
    # Allowed HTML tags for sanitization
    ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
    ALLOWED_ATTRIBUTES = {}
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required")
        
        email = email.strip().lower()
        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email format")
        
        if len(email) > 254:
            raise ValidationError("Email too long")
        
        return email
    
    @classmethod
    def validate_institute_email(cls, email: str) -> str:
        """Validate institute email"""
        email = cls.validate_email(email)
        if not email.endswith('@iiitdm.ac.in'):
            raise ValidationError("Only institute emails are allowed")
        return email
    
    @classmethod
    def validate_password(cls, password: str) -> str:
        """Validate password strength"""
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if len(password) > 128:
            raise ValidationError("Password too long")
        
        if not cls.PASSWORD_PATTERN.match(password):
            raise ValidationError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return password
    
    @classmethod
    def validate_student_id(cls, student_id: str) -> str:
        """Validate student ID format"""
        if not student_id or not isinstance(student_id, str):
            raise ValidationError("Student ID is required")
        
        student_id = student_id.strip()
        if not cls.STUDENT_ID_PATTERN.match(student_id):
            raise ValidationError("Invalid student ID format")
        
        return student_id
    
    @classmethod
    def validate_name(cls, name: str) -> str:
        """Validate name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Name is required")
        
        name = name.strip()
        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters long")
        
        if len(name) > 100:
            raise ValidationError("Name too long")
        
        # Allow only letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationError("Name contains invalid characters")
        
        return name
    
    @classmethod
    def validate_mess_choice(cls, mess: str) -> str:
        """Validate mess selection"""
        if not mess or not isinstance(mess, str):
            raise ValidationError("Mess selection is required")
        
        mess = mess.strip().lower()
        if mess not in ['mess1', 'mess2']:
            raise ValidationError("Invalid mess selection")
        
        return mess
    
    @classmethod
    def validate_rating(cls, rating: Any) -> int:
        """Validate rating value"""
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            raise ValidationError("Rating must be a number")
        
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        return rating
    
    @classmethod
    def validate_food_item(cls, food_item: str) -> str:
        """Validate food item name"""
        if not food_item or not isinstance(food_item, str):
            raise ValidationError("Food item is required")
        
        food_item = food_item.strip()
        if len(food_item) < 2:
            raise ValidationError("Food item name too short")
        
        if len(food_item) > 100:
            raise ValidationError("Food item name too long")
        
        # Allow letters, numbers, spaces, and common food characters
        if not re.match(r"^[a-zA-Z0-9\s\-'(),./]+$", food_item):
            raise ValidationError("Food item name contains invalid characters")
        
        return food_item
    
    @classmethod
    def validate_cost(cls, cost: Any) -> float:
        """Validate cost value"""
        try:
            cost = float(cost)
        except (ValueError, TypeError):
            raise ValidationError("Cost must be a number")
        
        if cost < 0:
            raise ValidationError("Cost cannot be negative")
        
        if cost > 10000:  # Reasonable upper limit
            raise ValidationError("Cost too high")
        
        return round(cost, 2)
    
    @classmethod
    def validate_floor(cls, floor: str) -> str:
        """Validate floor selection"""
        if not floor or not isinstance(floor, str):
            raise ValidationError("Floor is required")
        
        floor = floor.strip()
        if floor not in ['Ground', 'First', 'Second', 'Third']:
            raise ValidationError("Invalid floor selection")
        
        return floor
    
    @classmethod
    def validate_payment_mode(cls, payment_mode: str) -> str:
        """Validate payment mode"""
        if not payment_mode or not isinstance(payment_mode, str):
            raise ValidationError("Payment mode is required")
        
        payment_mode = payment_mode.strip().lower()
        if payment_mode not in ['cash', 'card', 'upi', 'online']:
            raise ValidationError("Invalid payment mode")
        
        return payment_mode
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Sanitize HTML content to prevent XSS"""
        if not text:
            return ""
        
        return bleach.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @classmethod
    def validate_comment(cls, comment: str) -> Optional[str]:
        """Validate and sanitize comment"""
        if not comment:
            return None
        
        comment = comment.strip()
        if len(comment) > 500:
            raise ValidationError("Comment too long (max 500 characters)")
        
        # Sanitize HTML
        comment = cls.sanitize_html(comment)
        
        return comment if comment else None
    
    @classmethod
    def validate_file_upload(cls, file: FileStorage, allowed_extensions: List[str], 
                           max_size: int = 5 * 1024 * 1024) -> FileStorage:
        """Validate file upload"""
        if not file or not file.filename:
            raise ValidationError("No file selected")
        
        # Check file extension
        if '.' not in file.filename:
            raise ValidationError("File must have an extension")
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
        
        # Check file size (if we can)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > max_size:
            raise ValidationError(f"File too large. Maximum size: {max_size // (1024*1024)}MB")
        
        return file
    
    @classmethod
    def validate_form_data(cls, form_data: Dict[str, Any], validation_rules: Dict[str, str]) -> Dict[str, Any]:
        """Validate form data based on rules"""
        validated_data = {}
        errors = {}
        
        for field, rule in validation_rules.items():
            try:
                value = form_data.get(field)
                
                if rule == 'email':
                    validated_data[field] = cls.validate_email(value)
                elif rule == 'institute_email':
                    validated_data[field] = cls.validate_institute_email(value)
                elif rule == 'password':
                    validated_data[field] = cls.validate_password(value)
                elif rule == 'student_id':
                    validated_data[field] = cls.validate_student_id(value)
                elif rule == 'name':
                    validated_data[field] = cls.validate_name(value)
                elif rule == 'mess_choice':
                    validated_data[field] = cls.validate_mess_choice(value)
                elif rule == 'rating':
                    validated_data[field] = cls.validate_rating(value)
                elif rule == 'food_item':
                    validated_data[field] = cls.validate_food_item(value)
                elif rule == 'cost':
                    validated_data[field] = cls.validate_cost(value)
                elif rule == 'floor':
                    validated_data[field] = cls.validate_floor(value)
                elif rule == 'payment_mode':
                    validated_data[field] = cls.validate_payment_mode(value)
                elif rule == 'comment':
                    validated_data[field] = cls.validate_comment(value)
                elif rule == 'required':
                    if not value:
                        raise ValidationError(f"{field} is required")
                    validated_data[field] = str(value).strip()
                
            except ValidationError as e:
                errors[field] = str(e)
        
        if errors:
            raise ValidationError(f"Validation errors: {errors}")
        
        return validated_data
