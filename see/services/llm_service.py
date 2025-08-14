"""
LLM-related services for ManageIt application
"""
import requests
import markdown
import logging
from typing import List
from flask import current_app
from app.services.feedback_service import FeedbackService

class LLMService:
    """Service class for LLM operations"""
    
    MESS_NAME_MAP = {
        "mess1": "Food Sutra",
        "mess2": "Shakti"
    }
    
    @classmethod
    def call_llm(cls, prompt: str, api_key: str, model: str = "llama-2-7b-chat", 
                 max_tokens: int = 500, platform: str = "groq") -> str:
        """
        Calls Groq API with LLaMA model to get text completion (summary).
        
        Args:
            prompt: The input text prompt for the model
            api_key: Your Groq API key
            model: Model name, default is "llama-2-7b-chat"
            max_tokens: Max tokens in response
            platform: API platform URL
            
        Returns:
            Generated text from model (summary)
        """
        if not api_key or not platform:
            raise ValueError("API key and platform URL are required")
        
        url = platform
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 1,
            "n": 1,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": model
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate response structure
            if "choices" not in data or not data["choices"]:
                raise ValueError("Invalid API response structure")
            
            if "message" not in data["choices"][0] or "content" not in data["choices"][0]["message"]:
                raise ValueError("Invalid API response format")
            
            return data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.Timeout:
            logging.error("LLM API request timed out")
            raise Exception("LLM API request timed out")
        except requests.exceptions.RequestException as e:
            logging.error(f"LLM API request failed: {e}")
            raise Exception(f"LLM API error: {e}")
        except (KeyError, IndexError, ValueError) as e:
            logging.error(f"Unexpected LLM API response format: {e}")
            raise Exception(f"Invalid LLM API response: {e}")
    
    @classmethod
    def summarize_feedback_text(cls, feedback_text: str) -> str:
        """Summarize critical feedback text using LLM"""
        if not feedback_text or not feedback_text.strip():
            return ""
        
        prompt = f"""
        You are generating a short, urgent **admin notification** based on student critical feedback.
        Rules:
        - Be brief and to the point (max 3–4 sentences).
        - Use a direct, alerting tone (no over-explanation).
        - Include only the key problem(s) without unnecessary details.
        - Keep it under 400 characters.
        - Focus on actionable issues that require immediate attention.

        Critical Feedback:
        {feedback_text}
        """

        try:
            api_key = current_app.config.get('GROQ_API_KEY')
            platform = current_app.config.get('GROQ_PLATFORM')
            model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
            
            if not api_key or not platform:
                logging.error("LLM configuration missing")
                return feedback_text[:400]  # Fallback to truncated original text
            
            summary = cls.call_llm(prompt, api_key, model=model, max_tokens=150, platform=platform)
            
            # Validate summary length
            if len(summary) > 400:
                summary = summary[:397] + "..."
            
            logging.info(f"Generated summary from LLM: {summary[:100]}...")
            return summary
            
        except Exception as e:
            logging.error(f"Failed to summarize feedback: {e}")
            return feedback_text[:400]  # Fallback to truncated original text
    
    @classmethod
    def create_admin_notification_from_critical_feedback(cls) -> List[str]:
        """Create admin notifications from critical feedback using LLM"""
        try:
            combined_texts = FeedbackService.get_critical_feedback_texts_for_llm()
            notifications = []
            
            for mess_key, feedback_text in combined_texts.items():
                if not feedback_text.strip():
                    logging.info(f"No critical feedback for {cls.MESS_NAME_MAP.get(mess_key, mess_key)}")
                    continue

                summary = cls.summarize_feedback_text(feedback_text)
                if not summary.strip():
                    logging.warning(f"LLM returned empty summary for {cls.MESS_NAME_MAP.get(mess_key, mess_key)}")
                    summary = feedback_text[:400]  # Fallback

                # Convert markdown to HTML safely
                try:
                    summary_html = markdown.markdown(summary, extensions=["nl2br"])
                except Exception as e:
                    logging.error(f"Markdown conversion failed: {e}")
                    summary_html = summary.replace('\n', '<br>')

                # Add mess name as heading in HTML
                mess_name = cls.MESS_NAME_MAP.get(mess_key, mess_key)
                mess_html_section = f"<h3>{mess_name}</h3>\n{summary_html}"
                notifications.append(mess_html_section)

            return notifications
            
        except Exception as e:
            logging.error(f"Failed to create admin notifications: {e}")
            return []
