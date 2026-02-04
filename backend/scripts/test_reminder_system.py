"""
Complete Reminder System Test

This script:
1. Creates a test user with profile and phone number
2. Creates a reminder that fires in the next 2-3 minutes
3. Verifies the reminder scheduler picks it up and sends SMS

Run from backend directory:
    python scripts/test_reminder_system.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Add the backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from sqlalchemy import select
from app.db import async_session_maker, init_db
from app.models import User, UserProfile, Reminder
from app.security import hash_password


async def create_test_user_and_reminder():
    """Create a test user with profile and a reminder that fires soon."""
    
    print("=" * 70)
    print("CO-CODE REMINDER SYSTEM TEST")
    print("=" * 70)
    
    # Initialize database
    print("\n1. Initializing database...")
    await init_db()
    print("   ✅ Database initialized")
    
    async with async_session_maker() as db:
        # Check for existing test user
        print("\n2. Creating/finding test user...")
        result = await db.execute(
            select(User).where(User.email == "reminder_test@cocode.com")
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"   ℹ️  Found existing test user: {user.email} (ID: {user.id})")
        else:
            # Create test user
            user = User(
                id=uuid4(),
                email="reminder_test@cocode.com",
                full_name="Reminder Test User",
                password_hash=hash_password("testpass123"),
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"   ✅ Created test user: {user.email} (ID: {user.id})")
        
        # Check for profile
        print("\n3. Creating/updating user profile...")
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()
        
        # Get phone number from environment
        import os
        phone_number = os.getenv("SMS_TEST_TO_NUMBER", "+919004281995")
        
        if profile:
            profile.phone_number = phone_number
            profile.full_name = "Reminder Test User"
            profile.age_years = 30
            print(f"   ℹ️  Updated existing profile with phone: {phone_number}")
        else:
            profile = UserProfile(
                user_id=user.id,
                full_name="Reminder Test User",
                phone_number=phone_number,
                age_years=30,
                sex_at_birth="male",
                height_cm=175,
                weight_kg=70
            )
            db.add(profile)
            print(f"   ✅ Created profile with phone: {phone_number}")
        
        await db.commit()
        await db.refresh(profile)
        
        # Delete any existing test reminders for this user
        print("\n4. Cleaning up old test reminders...")
        result = await db.execute(
            select(Reminder).where(Reminder.user_id == user.id)
        )
        old_reminders = list(result.scalars().all())
        for reminder in old_reminders:
            await db.delete(reminder)
        await db.commit()
        print(f"   ✅ Deleted {len(old_reminders)} old reminder(s)")
        
        # Create a new reminder that fires in 2 minutes
        print("\n5. Creating test reminder...")
        next_run = datetime.utcnow() + timedelta(minutes=2)
        
        reminder = Reminder(
            user_id=user.id,
            type="test",
            title="🧪 Test Reminder",
            message=f"This is a test reminder from Co-Code! If you receive this SMS, the reminder system is working perfectly. Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}",
            schedule_type="once",
            schedule_json={"time": next_run.isoformat()},
            timezone="UTC",
            channel="sms",
            is_enabled=True,
            next_run_at=next_run
        )
        
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        
        print(f"   ✅ Created test reminder:")
        print(f"      ID: {reminder.id}")
        print(f"      Title: {reminder.title}")
        print(f"      Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"      Phone: {phone_number}")
        
        # Calculate time until reminder fires
        seconds_until = (next_run - datetime.utcnow()).total_seconds()
        minutes = int(seconds_until // 60)
        seconds = int(seconds_until % 60)
        
        print(f"\n{'=' * 70}")
        print(f"⏰ REMINDER WILL FIRE IN: {minutes} minutes and {seconds} seconds")
        print(f"{'=' * 70}")
        print(f"\n📱 Watch for SMS to: {phone_number}")
        print(f"📋 Check Docker logs: docker logs ggw-backend -f")
        print(f"🔍 Look for: 'Reminder scheduler tick: processed'")
        print(f"\nThe reminder scheduler checks every 60 seconds.")
        print(f"Your reminder will be sent at approximately: {next_run.strftime('%H:%M:%S UTC')}")
        print(f"\n{'=' * 70}\n")
        
        return {
            "user_id": str(user.id),
            "reminder_id": str(reminder.id),
            "phone_number": phone_number,
            "next_run": next_run.isoformat(),
            "seconds_until": int(seconds_until)
        }


async def monitor_logs():
    """Monitor Docker logs for reminder processing."""
    print("\n🔍 Monitoring logs for reminder processing...")
    print("   (Press Ctrl+C to stop)\n")
    
    import subprocess
    
    try:
        process = subprocess.Popen(
            ["docker", "logs", "ggw-backend", "-f"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            if any(keyword in line.lower() for keyword in ["reminder", "sms", "twilio", "processed"]):
                print(f"   {line.strip()}")
        
    except KeyboardInterrupt:
        print("\n\n   Monitoring stopped by user")
        process.kill()


if __name__ == "__main__":
    try:
        result = asyncio.run(create_test_user_and_reminder())
        
        print("\n" + "=" * 70)
        print("TEST SETUP COMPLETE!")
        print("=" * 70)
        print("\nWould you like to monitor logs? (Y/n): ", end="")
        
        choice = input().strip().lower()
        if choice in ["", "y", "yes"]:
            asyncio.run(monitor_logs())
        else:
            print("\n✅ Setup complete. Check SMS and Docker logs in ~2 minutes.")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
