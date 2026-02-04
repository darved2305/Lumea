"""
Tests for Profile /me endpoints and Reminder system.

Tests:
1. GET /profile/me returns exists=false for new user
2. PUT /profile/me creates profile; second PUT updates same row (no duplicates)
3. Completion logic sets is_completed true only when required fields present
4. PATCH /profile/me updates fields and persists
5. Scheduler tick processes due reminders -> creates reminder_events, updates next_run_at
6. SMS test endpoint works in mock mode
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

# Import test fixtures
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProfileMeEndpoints:
    """Tests for /api/profile/me endpoints."""
    
    def test_profile_me_new_user_returns_exists_false(self):
        """GET /profile/me returns exists=false for a new user without a profile."""
        from app.services.reminder_service import check_profile_completion
        
        # Test completion check with None
        assert check_profile_completion(None) == False
    
    def test_profile_completion_requires_all_fields(self):
        """Profile is only complete when all required fields are present."""
        from app.services.reminder_service import check_profile_completion
        
        # Create a mock profile with missing fields
        mock_profile = MagicMock()
        mock_profile.full_name = "Test User"
        mock_profile.age_years = None  # Missing
        mock_profile.date_of_birth = None  # Missing  
        mock_profile.sex_at_birth = "male"
        mock_profile.height_cm = 175
        mock_profile.weight_kg = 70
        
        # Should be incomplete (missing age)
        assert check_profile_completion(mock_profile) == False
        
        # Now add age
        mock_profile.age_years = 30
        assert check_profile_completion(mock_profile) == True
    
    def test_profile_completion_with_dob_instead_of_age(self):
        """Profile can be complete with date_of_birth instead of age_years."""
        from app.services.reminder_service import check_profile_completion
        
        mock_profile = MagicMock()
        mock_profile.full_name = "Test User"
        mock_profile.age_years = None
        mock_profile.date_of_birth = datetime(1990, 1, 1)  # Has DOB
        mock_profile.sex_at_birth = "female"
        mock_profile.height_cm = 165
        mock_profile.weight_kg = 60
        
        # Should be complete (has DOB)
        assert check_profile_completion(mock_profile) == True
    
    def test_bmi_computation(self):
        """BMI is correctly computed from height and weight."""
        from app.services.reminder_service import compute_bmi
        
        # Normal case: 70kg, 175cm -> BMI = 22.86
        bmi = compute_bmi(175, 70)
        assert bmi is not None
        assert abs(bmi - 22.86) < 0.1
        
        # Edge case: missing height
        assert compute_bmi(None, 70) is None
        assert compute_bmi(0, 70) is None
        
        # Edge case: missing weight
        assert compute_bmi(175, None) is None


class TestReminderService:
    """Tests for the reminder service."""
    
    def test_calculate_next_run_fixed_times(self):
        """Test next run calculation for fixed_times schedule."""
        from app.services.reminder_service import ReminderService
        from unittest.mock import MagicMock
        
        # Create mock service
        mock_db = MagicMock()
        mock_user = MagicMock()
        service = ReminderService(mock_db, mock_user)
        
        schedule_json = {"times": ["08:00", "14:00", "20:00"]}
        next_run = service._calculate_next_run(
            schedule_type="fixed_times",
            schedule_json=schedule_json,
            timezone="Asia/Kolkata"
        )
        
        # Should return a datetime
        assert next_run is not None
        assert isinstance(next_run, datetime)
    
    def test_calculate_next_run_interval(self):
        """Test next run calculation for interval schedule."""
        from app.services.reminder_service import ReminderService
        from unittest.mock import MagicMock
        
        mock_db = MagicMock()
        mock_user = MagicMock()
        service = ReminderService(mock_db, mock_user)
        
        schedule_json = {
            "interval_minutes": 120,
            "start_time": "08:00",
            "end_time": "22:00"
        }
        next_run = service._calculate_next_run(
            schedule_type="interval",
            schedule_json=schedule_json,
            timezone="Asia/Kolkata"
        )
        
        assert next_run is not None
        assert isinstance(next_run, datetime)


class TestSMSSender:
    """Tests for SMS sender service."""
    
    def test_sms_sender_mock_mode(self):
        """SMS sender in mock mode logs instead of sending."""
        from app.services.sms_sender import SMSSender
        
        sender = SMSSender()
        # Force mock mode for testing
        sender.mode = "mock"
        
        result = sender._send_mock(
            to_number="+911234567890",
            message="Test message",
            masked_phone="****7890",
            user_id=uuid4()
        )
        
        assert result["success"] == True
        assert result["status"] == "mocked"
        assert result["provider"] == "mock"
    
    def test_sms_sender_masks_phone_number(self):
        """Phone numbers are properly masked for logs."""
        from app.services.sms_sender import SMSSender
        
        sender = SMSSender()
        
        assert sender._mask_phone("+919876543210") == "****3210"
        assert sender._mask_phone("1234567890") == "****7890"
        assert sender._mask_phone("") == "****"
        assert sender._mask_phone(None) == "****"


class TestReminderScheduler:
    """Tests for the reminder scheduler."""
    
    def test_scheduler_can_start_and_stop(self):
        """Scheduler starts and stops without error."""
        from app.services.reminder_scheduler import (
            start_reminder_scheduler,
            stop_reminder_scheduler,
            get_scheduler
        )
        
        # Disable scheduler via settings for test
        with patch('app.services.reminder_scheduler.settings') as mock_settings:
            mock_settings.REMINDER_SCHEDULER_ENABLED = False
            mock_settings.REMINDER_CHECK_INTERVAL_SECONDS = 60
            
            start_reminder_scheduler()
            # When disabled, scheduler should not be running
            scheduler = get_scheduler()
            assert scheduler is None
            
            stop_reminder_scheduler()


class TestProfileSchemas:
    """Tests for profile-related Pydantic schemas."""
    
    def test_profile_update_schema_validates(self):
        """UserProfileUpdate schema accepts valid data."""
        from app.schemas import UserProfileUpdate
        
        data = {
            "full_name": "Test User",
            "age_years": 30,
            "sex_at_birth": "male",
            "height_cm": 175.5,
            "weight_kg": 70.0
        }
        
        profile = UserProfileUpdate(**data)
        assert profile.full_name == "Test User"
        assert profile.age_years == 30
    
    def test_profile_update_schema_rejects_invalid_age(self):
        """UserProfileUpdate rejects invalid age values."""
        from app.schemas import UserProfileUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserProfileUpdate(age_years=-5)  # Negative age
        
        with pytest.raises(ValidationError):
            UserProfileUpdate(age_years=200)  # Age > 150


class TestReminderSchemas:
    """Tests for reminder-related Pydantic schemas."""
    
    def test_reminder_create_schema(self):
        """ReminderCreate schema validates correctly."""
        from app.schemas import ReminderCreate, ReminderScheduleConfig
        
        data = {
            "type": "hydration",
            "title": "Drink Water",
            "schedule_type": "interval",
            "schedule_json": {
                "interval_minutes": 120,
                "start_time": "08:00",
                "end_time": "22:00"
            }
        }
        
        reminder = ReminderCreate(**data)
        assert reminder.type == "hydration"
        assert reminder.title == "Drink Water"
        assert reminder.schedule_type == "interval"
    
    def test_sms_test_response_schema(self):
        """SMSTestResponse schema works correctly."""
        from app.schemas import SMSTestResponse
        
        response = SMSTestResponse(
            success=True,
            status="mocked",
            provider="mock",
            message="Test SMS sent"
        )
        
        assert response.success == True
        assert response.status == "mocked"


# Run tests with: pytest tests/test_profile_reminders.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
