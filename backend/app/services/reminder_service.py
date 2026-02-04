"""
Reminder Service

Handles CRUD operations for reminders and processes due reminders.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import pytz

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Reminder, ReminderEvent, UserProfile, User
from app.services.sms_sender import get_sms_sender

logger = logging.getLogger(__name__)

# Required fields for profile completion
REQUIRED_PROFILE_FIELDS = ["full_name", "age_years", "sex_at_birth", "height_cm", "weight_kg"]


class ReminderService:
    """Service for managing user reminders."""
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.sms_sender = get_sms_sender()
    
    async def get_all(self) -> List[Reminder]:
        """Get all reminders for the current user."""
        result = await self.db.execute(
            select(Reminder)
            .where(Reminder.user_id == self.user.id)
            .order_by(Reminder.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_id(self, reminder_id: UUID) -> Optional[Reminder]:
        """Get a specific reminder by ID."""
        result = await self.db.execute(
            select(Reminder)
            .where(and_(
                Reminder.id == reminder_id,
                Reminder.user_id == self.user.id
            ))
        )
        return result.scalar_one_or_none()
    
    async def create(self, data: Dict[str, Any]) -> Reminder:
        """Create a new reminder."""
        # Calculate next_run_at based on schedule
        next_run = self._calculate_next_run(
            schedule_type=data["schedule_type"],
            schedule_json=data["schedule_json"],
            timezone=data.get("timezone", "Asia/Kolkata")
        )
        
        reminder = Reminder(
            user_id=self.user.id,
            type=data["type"],
            title=data["title"],
            message=data.get("message"),
            schedule_type=data["schedule_type"],
            schedule_json=data["schedule_json"] if isinstance(data["schedule_json"], dict) else data["schedule_json"].model_dump(),
            timezone=data.get("timezone", "Asia/Kolkata"),
            channel=data.get("channel", "sms"),
            medicine_id=data.get("medicine_id"),
            medicine_name=data.get("medicine_name"),
            is_enabled=data.get("is_enabled", True),
            next_run_at=next_run
        )
        
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        
        logger.info(f"Created reminder {reminder.id} for user {self.user.id}: {reminder.title}")
        return reminder
    
    async def update(self, reminder_id: UUID, data: Dict[str, Any]) -> Optional[Reminder]:
        """Update an existing reminder."""
        reminder = await self.get_by_id(reminder_id)
        if not reminder:
            return None
        
        # Update fields if provided
        for field in ["title", "message", "channel", "is_enabled", "timezone"]:
            if field in data and data[field] is not None:
                setattr(reminder, field, data[field])
        
        # Update schedule if changed
        if "schedule_type" in data or "schedule_json" in data:
            schedule_type = data.get("schedule_type", reminder.schedule_type)
            schedule_json = data.get("schedule_json", reminder.schedule_json)
            
            if hasattr(schedule_json, "model_dump"):
                schedule_json = schedule_json.model_dump()
            
            reminder.schedule_type = schedule_type
            reminder.schedule_json = schedule_json
            
            # Recalculate next run
            reminder.next_run_at = self._calculate_next_run(
                schedule_type=schedule_type,
                schedule_json=schedule_json,
                timezone=data.get("timezone", reminder.timezone)
            )
        
        reminder.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(reminder)
        
        logger.info(f"Updated reminder {reminder.id} for user {self.user.id}")
        return reminder
    
    async def delete(self, reminder_id: UUID) -> bool:
        """Delete a reminder."""
        reminder = await self.get_by_id(reminder_id)
        if not reminder:
            return False
        
        await self.db.delete(reminder)
        await self.db.commit()
        
        logger.info(f"Deleted reminder {reminder_id} for user {self.user.id}")
        return True
    
    async def generate_default_reminders(self) -> List[Reminder]:
        """
        Generate default reminders based on user profile.
        
        Creates hydration and sleep reminders if not already existing.
        """
        # Get user profile
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == self.user.id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.warning(f"No profile found for user {self.user.id}, skipping default reminders")
            return []
        
        created_reminders = []
        
        # Check existing reminders
        existing = await self.get_all()
        existing_types = {r.type for r in existing}
        
        # 1. Hydration reminder (if not exists)
        if "hydration" not in existing_types:
            hydration = await self.create({
                "type": "hydration",
                "title": "💧 Stay Hydrated",
                "message": "Time to drink some water! Staying hydrated helps maintain energy and focus.",
                "schedule_type": "interval",
                "schedule_json": {
                    "interval_minutes": 120,
                    "start_time": "08:00",
                    "end_time": "22:00"
                },
                "channel": "sms" if profile.phone_number else "in_app"
            })
            created_reminders.append(hydration)
        
        # 2. Sleep reminder (based on sleep_hours_avg)
        if "sleep" not in existing_types:
            bedtime = "22:00"  # Default
            if profile.sleep_hours_avg:
                # Calculate bedtime based on average sleep hours (assume 6:30 AM wake)
                wake_hour = 6.5
                bed_hour = (wake_hour - profile.sleep_hours_avg) % 24
                bedtime = f"{int(bed_hour):02d}:{int((bed_hour % 1) * 60):02d}"
            
            sleep = await self.create({
                "type": "sleep",
                "title": "🌙 Time for Bed",
                "message": f"It's time to wind down. Aim for {profile.sleep_hours_avg or 7-8} hours of quality sleep.",
                "schedule_type": "fixed_times",
                "schedule_json": {"times": [bedtime]},
                "channel": "sms" if profile.phone_number else "in_app"
            })
            created_reminders.append(sleep)
        
        # 3. Exercise reminder (if activity_level is sedentary)
        if "exercise" not in existing_types and profile.activity_level == "sedentary":
            exercise = await self.create({
                "type": "exercise",
                "title": "🏃 Get Moving!",
                "message": "A short walk or stretch can boost your energy. Try 10 minutes of movement.",
                "schedule_type": "fixed_times",
                "schedule_json": {"times": ["10:00", "15:00"]},
                "channel": "in_app"  # Don't spam SMS for exercise
            })
            created_reminders.append(exercise)
        
        logger.info(f"Generated {len(created_reminders)} default reminders for user {self.user.id}")
        return created_reminders
    
    def _calculate_next_run(
        self,
        schedule_type: str,
        schedule_json: Dict[str, Any],
        timezone: str = "Asia/Kolkata"
    ) -> Optional[datetime]:
        """Calculate the next run time based on schedule configuration."""
        try:
            tz = pytz.timezone(timezone)
            now_local = datetime.now(tz)
            
            if schedule_type == "fixed_times":
                times = schedule_json.get("times", [])
                if not times:
                    return None
                
                # Find next occurrence
                for time_str in sorted(times):
                    hour, minute = map(int, time_str.split(":"))
                    next_time = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if next_time > now_local:
                        return next_time.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # All times passed today, schedule for tomorrow
                first_time = sorted(times)[0]
                hour, minute = map(int, first_time.split(":"))
                next_time = (now_local + timedelta(days=1)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                return next_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            elif schedule_type == "interval":
                interval_minutes = schedule_json.get("interval_minutes", 60)
                start_time = schedule_json.get("start_time", "08:00")
                end_time = schedule_json.get("end_time", "22:00")
                
                start_h, start_m = map(int, start_time.split(":"))
                end_h, end_m = map(int, end_time.split(":"))
                
                start_dt = now_local.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                end_dt = now_local.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                
                if now_local < start_dt:
                    next_time = start_dt
                elif now_local > end_dt:
                    # Schedule for tomorrow
                    next_time = (start_dt + timedelta(days=1))
                else:
                    # Calculate next interval
                    next_time = now_local + timedelta(minutes=interval_minutes)
                    if next_time > end_dt:
                        next_time = (start_dt + timedelta(days=1))
                
                return next_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            elif schedule_type == "cron":
                # For cron, we'd need a cron parser - simplified for MVP
                # Default to next hour
                next_time = now_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                return next_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return None


async def process_due_reminders(db: AsyncSession) -> int:
    """
    Process all due reminders (called by scheduler).
    
    Returns number of reminders processed.
    """
    now = datetime.utcnow()
    sms_sender = get_sms_sender()
    processed = 0
    
    try:
        # Find all due reminders
        result = await db.execute(
            select(Reminder)
            .options(selectinload(Reminder.user))
            .where(and_(
                Reminder.is_enabled == True,
                Reminder.next_run_at <= now
            ))
            .order_by(Reminder.next_run_at)
        )
        due_reminders = list(result.scalars().all())
        
        if not due_reminders:
            return 0
        
        logger.info(f"Processing {len(due_reminders)} due reminders")
        
        for reminder in due_reminders:
            try:
                # Get user's phone number from profile
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == reminder.user_id)
                )
                profile = profile_result.scalar_one_or_none()
                phone_number = profile.phone_number if profile else None
                
                # Determine if we should send SMS
                should_send_sms = (
                    reminder.channel == "sms" and 
                    phone_number is not None
                )
                
                # Send notification
                if should_send_sms:
                    sms_result = await sms_sender.send(
                        to_number=phone_number,
                        message=f"{reminder.title}\n{reminder.message or ''}".strip(),
                        user_id=reminder.user_id,
                        reminder_id=reminder.id
                    )
                    status = sms_result["status"]
                    provider = sms_result["provider"]
                    provider_response = sms_result.get("provider_response")
                    error_message = sms_result.get("error")
                else:
                    # In-app or no phone number - skip SMS
                    status = "skipped"
                    provider = "in_app"
                    provider_response = {"reason": "No phone number or channel is in_app"}
                    error_message = None
                
                # Create event record
                event = ReminderEvent(
                    reminder_id=reminder.id,
                    user_id=reminder.user_id,
                    status=status,
                    provider=provider,
                    provider_response=provider_response,
                    message_sent=f"{reminder.title}\n{reminder.message or ''}".strip() if should_send_sms else None,
                    phone_number=phone_number[-4:] if phone_number else None,  # Masked
                    error_message=error_message
                )
                db.add(event)
                
                # Update reminder's last_run_at and next_run_at
                reminder.last_run_at = now
                
                # Calculate next run
                service = ReminderService(db, reminder.user)
                reminder.next_run_at = service._calculate_next_run(
                    schedule_type=reminder.schedule_type,
                    schedule_json=reminder.schedule_json,
                    timezone=reminder.timezone
                )
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing reminder {reminder.id}: {e}")
                # Still record the failed event
                event = ReminderEvent(
                    reminder_id=reminder.id,
                    user_id=reminder.user_id,
                    status="failed",
                    provider="error",
                    error_message=str(e)
                )
                db.add(event)
        
        await db.commit()
        logger.info(f"Processed {processed} reminders successfully")
        
    except Exception as e:
        logger.error(f"Error in process_due_reminders: {e}")
        await db.rollback()
    
    return processed


def check_profile_completion(profile: UserProfile) -> bool:
    """
    Check if a profile has all required fields filled.
    
    Required fields: full_name, age_years (or date_of_birth), sex_at_birth, height_cm, weight_kg
    """
    if not profile:
        return False
    
    # Check required fields
    if not profile.full_name:
        return False
    
    # Age: need either age_years or date_of_birth
    if not profile.age_years and not profile.date_of_birth:
        return False
    
    if not profile.sex_at_birth:
        return False
    
    if not profile.height_cm:
        return False
    
    if not profile.weight_kg:
        return False
    
    return True


def compute_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Optional[float]:
    """Compute BMI from height and weight."""
    if not height_cm or not weight_kg or height_cm <= 0:
        return None
    
    height_m = height_cm / 100
    bmi = weight_kg / (height_m * height_m)
    return round(bmi, 2)
