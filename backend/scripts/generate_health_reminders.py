"""
Generate Health Reminders for Existing Users

Creates reminders based on user profile data:
- Hydration reminders
- Sleep reminders
- Medicine reminders (if any)
- Exercise reminders
"""
import sys
sys.path.insert(0, '/app')

import asyncio
from datetime import datetime, timedelta, time as dt_time
from sqlalchemy import select
from app.db import async_session_maker
from app.models import User, UserProfile, Reminder
from app.services.reminder_service import ReminderService

async def generate_reminders():
    print("=" * 70)
    print("GENERATING HEALTH REMINDERS")
    print("=" * 70)
    
    async with async_session_maker() as db:
        # Get all users with profiles and phone numbers
        result = await db.execute(
            select(User, UserProfile)
            .join(UserProfile)
            .where(UserProfile.phone_number.isnot(None))
        )
        users = result.all()
        
        if not users:
            print("\n❌ No users with phone numbers found!")
            return
        
        print(f"\nFound {len(users)} user(s) with phone numbers")
        
        for user, profile in users:
            print(f"\n{'─' * 70}")
            print(f"User: {user.email}")
            print(f"Phone: {profile.phone_number}")
            print(f"Age: {profile.age_years}, Activity: {profile.activity_level or 'not set'}")
            
            # Delete old non-medicine reminders
            result = await db.execute(
                select(Reminder)
                .where(Reminder.user_id == user.id)
                .where(Reminder.type.in_(['hydration', 'sleep', 'exercise', 'test']))
            )
            old_reminders = list(result.scalars().all())
            for r in old_reminders:
                await db.delete(r)
            await db.commit()
            print(f"  Cleaned up {len(old_reminders)} old reminder(s)")
            
            reminders_created = []
            
            # 1. HYDRATION REMINDER - Every 2 hours during day
            print("\n  Creating hydration reminders...")
            now = datetime.utcnow()
            # Schedule next hydration in 3 minutes for testing
            next_hydration = now + timedelta(minutes=3)
            
            hydration = Reminder(
                user_id=user.id,
                type='hydration',
                title='💧 Stay Hydrated',
                message='Time to drink water! Staying hydrated helps maintain energy and focus throughout the day. 🚰',
                schedule_type='interval',
                schedule_json={
                    'interval_minutes': 120,  # Every 2 hours
                    'start_time': '08:00',
                    'end_time': '22:00'
                },
                timezone='Asia/Kolkata',
                channel='sms',
                is_enabled=True,
                next_run_at=next_hydration
            )
            db.add(hydration)
            reminders_created.append(('💧 Hydration', next_hydration))
            
            # 2. SLEEP REMINDER - Every night
            print("  Creating sleep reminder...")
            # Calculate next 22:00 or tomorrow if passed
            now_hour = now.hour
            if now_hour >= 22:
                next_sleep = (now + timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
            else:
                next_sleep = now.replace(hour=22, minute=0, second=0, microsecond=0)
            
            # For testing, set to 5 minutes from now
            next_sleep = now + timedelta(minutes=5)
            
            sleep = Reminder(
                user_id=user.id,
                type='sleep',
                title='🌙 Time for Bed',
                message=f'Wind down time! Aim for 7-8 hours of quality sleep for better health. Good night! 😴',
                schedule_type='fixed_times',
                schedule_json={'times': ['22:00']},
                timezone='Asia/Kolkata',
                channel='sms',
                is_enabled=True,
                next_run_at=next_sleep
            )
            db.add(sleep)
            reminders_created.append(('🌙 Sleep', next_sleep))
            
            # 3. EXERCISE REMINDER - if sedentary
            if profile.activity_level in ['sedentary', None]:
                print("  Creating exercise reminder...")
                # Set to 7 minutes from now for testing
                next_exercise = now + timedelta(minutes=7)
                
                exercise = Reminder(
                    user_id=user.id,
                    type='exercise',
                    title='🏃 Get Moving!',
                    message='Time for some movement! A short 10-minute walk or stretch can boost your energy and improve your health. 💪',
                    schedule_type='fixed_times',
                    schedule_json={'times': ['10:00', '15:00']},
                    timezone='Asia/Kolkata',
                    channel='sms',
                    is_enabled=True,
                    next_run_at=next_exercise
                )
                db.add(exercise)
                reminders_created.append(('🏃 Exercise', next_exercise))
            
            await db.commit()
            
            print(f"\n  ✅ Created {len(reminders_created)} reminders:")
            for title, next_run in reminders_created:
                minutes_until = (next_run - now).total_seconds() / 60
                print(f"     {title}: fires in {int(minutes_until)} minutes ({next_run.strftime('%H:%M UTC')})")
    
    print(f"\n{'=' * 70}")
    print("✅ REMINDER GENERATION COMPLETE!")
    print("=" * 70)
    print("\n📱 Reminders will be sent via SMS")
    print("🔍 Monitor logs: docker logs -f ggw-backend 2>&1 | grep -i reminder")
    print(f"\n⏰ Next reminders:")
    print(f"   - Hydration: ~3 minutes")
    print(f"   - Sleep: ~5 minutes")
    print(f"   - Exercise: ~7 minutes")
    print("\n" + "=" * 70)

asyncio.run(generate_reminders())
