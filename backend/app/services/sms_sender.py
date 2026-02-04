"""
SMS Sender Service

Handles sending SMS messages via Twilio or mock mode.
Never hardcodes phone numbers - all values come from DB or env vars.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.settings import settings

logger = logging.getLogger(__name__)


class SMSSender:
    """SMS sending service with Twilio and mock support."""
    
    def __init__(self):
        self.mode = settings.SMS_MODE
        self.twilio_client = None
        
        # Initialize Twilio client if configured
        if self.mode == "twilio" and self._has_twilio_config():
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio client: {e}. Falling back to mock mode.")
                self.mode = "mock"
        elif self.mode == "twilio":
            logger.warning("Twilio credentials not configured. Using mock mode.")
            self.mode = "mock"
    
    def _has_twilio_config(self) -> bool:
        """Check if Twilio credentials are configured."""
        return all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_FROM_NUMBER
        ])
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for logging (show last 4 digits only)."""
        if not phone or len(phone) < 4:
            return "****"
        return f"****{phone[-4:]}"
    
    async def send(
        self,
        to_number: str,
        message: str,
        user_id: Optional[UUID] = None,
        reminder_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to_number: Recipient phone number (from DB, not hardcoded!)
            message: Message content
            user_id: Optional user ID for logging
            reminder_id: Optional reminder ID for logging
            
        Returns:
            Dict with status, provider, and response details
        """
        if not to_number:
            logger.error(f"SMS send failed: No phone number provided (user_id={user_id})")
            return {
                "success": False,
                "status": "failed",
                "provider": "none",
                "error": "No phone number provided",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        masked_phone = self._mask_phone(to_number)
        
        if self.mode == "twilio" and self.twilio_client:
            return await self._send_twilio(to_number, message, masked_phone, user_id)
        else:
            return self._send_mock(to_number, message, masked_phone, user_id)
    
    async def _send_twilio(
        self,
        to_number: str,
        message: str,
        masked_phone: str,
        user_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        try:
            logger.info(f"Attempting to send SMS via Twilio to {masked_phone}")
            logger.debug(f"From: {settings.TWILIO_FROM_NUMBER}, To: {to_number}")
            
            result = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=to_number
            )
            
            logger.info(f"✅ SMS sent via Twilio to {masked_phone} (user_id={user_id}, sid={result.sid})")
            
            return {
                "success": True,
                "status": "sent",
                "provider": "twilio",
                "provider_response": {
                    "sid": result.sid,
                    "status": result.status,
                    "date_created": str(result.date_created) if result.date_created else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Twilio SMS failed to {masked_phone} (user_id={user_id}): {type(e).__name__}: {str(e)}")
            return {
                "success": False,
                "status": "failed",
                "provider": "twilio",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _send_mock(
        self,
        to_number: str,
        message: str,
        masked_phone: str,
        user_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Mock SMS sending (logs + returns success)."""
        logger.info(
            f"[MOCK SMS] To: {masked_phone}, User: {user_id}\n"
            f"  Message: {message[:100]}{'...' if len(message) > 100 else ''}"
        )
        
        return {
            "success": True,
            "status": "mocked",
            "provider": "mock",
            "provider_response": {
                "mocked": True,
                "to": masked_phone,
                "message_preview": message[:50] + "..." if len(message) > 50 else message
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def send_test(self, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a test SMS to the configured test number (from env).
        
        This is ONLY for testing - uses SMS_TEST_TO_NUMBER from environment.
        """
        test_number = settings.SMS_TEST_TO_NUMBER
        
        if not test_number:
            return {
                "success": False,
                "status": "failed",
                "provider": "none",
                "error": "SMS_TEST_TO_NUMBER not configured in environment",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        test_message = message or "🏥 Lumea Health Test: Your SMS configuration is working!"
        
        return await self.send(
            to_number=test_number,
            message=test_message,
            user_id=None,
            reminder_id=None
        )


# Singleton instance
_sms_sender: Optional[SMSSender] = None


def get_sms_sender() -> SMSSender:
    """Get or create the SMS sender singleton."""
    global _sms_sender
    if _sms_sender is None:
        _sms_sender = SMSSender()
    return _sms_sender
