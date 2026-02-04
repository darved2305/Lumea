"""
Create Test Reminder for E2E Verification

Creates a reminder that will fire in 2 minutes to test the full flow.
Run inside Docker: docker exec ggw-backend python scripts/create_test_reminder.py
"""
import sys
sys.path.insert(0, '/app')

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from app.db import async_session_maker
from app.models import User, UserProfile, Reminder
from app.security import hash_password

async def create_test_reminder():
    """Create a test reminder that fires soon."""
    
    # Import inside function to ensure proper module loading
    from app.db import async_session_maker
    from app.models import User, UserProfile, Reminder
    from sqlalchemy import select
    
    print("=" * 60)
    print("CREATING TEST REMINDER")
    print("=" * 60)
    
    async with async_session_maker() as db:
        # Find a user with a phone number in their profile
        result = await db.execute(
            select(User).join(UserProfile).where(UserProfile.phone_number.isnot(None)).limit(1)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("\n❌ No user with phone number found!")
            print("   Please create a user profile with a phone number first.")
            
            # List all users
            all_users = await db.execute(select(User).limit(5))
            users = list(all_users.scalars().all())
            if users:
                print("\n   Available users:")
                for u in users:
                    print(f"   - {u.email} (id: {u.id})")
            return
        
        # Get user's profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()
        
        print(f"\nFound user: {user.email}")
        print(f"Phone number: ****{profile.phone_number[-4:] if profile and profile.phone_number else 'N/A'}")
        
        # Create a reminder that fires in 2 minutes
        next_run = datetime.utcnow() + timedelta(minutes=2)
        
        reminder = Reminder(
            user_id=user.id,
            type="test",
            title="🧪 Test Reminder",
            message="This is a test reminder from Lumea Health! If you received this, the SMS system is working correctly.",
            schedule_type="fixed_times",
            schedule_json={"times": [next_run.strftime("%H:%M")]},
            timezone="UTC",
            channel="sms",
            is_enabled=True,
            next_run_at=next_run
        )
        
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        
        print(f"\n✅ Created test reminder!")
        print(f"   ID: {reminder.id}")
        print(f"   Title: {reminder.title}")
        print(f"   Next Run: {reminder.next_run_at} UTC")
        print(f"   (approximately {2} minutes from now)")
        
        print(f"\n⏰ The reminder scheduler runs every 60 seconds.")
        print(f"   Watch the logs: docker logs -f ggw-backend 2>&1 | grep -i 'reminder\\|SMS\\|twilio'")
        
        return reminder


if __name__ == "__main__":
    asyncio.run(create_test_reminder())
