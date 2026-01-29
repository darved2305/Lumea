"""
Database migration script for Health Chat feature.
Run this after updating your .env with DATABASE_URL
"""
import asyncio
from app.db import engine, Base
from app.models import User, LoginEvent, PatientProfile, ChatSession, ChatMessage

async def run_migration():
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Drop all tables (use with caution in production!)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database migration completed successfully!")
    print("\nCreated tables:")
    print("  - users")
    print("  - login_events")
    print("  - patient_profiles")
    print("  - chat_sessions")
    print("  - chat_messages")

if __name__ == "__main__":
    asyncio.run(run_migration())
