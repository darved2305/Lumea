"""
Migration: Add extraction metadata fields

Run this migration to add new fields for enhanced extraction tracking
"""
from sqlalchemy import text
import asyncio
from app.db import get_db


async def migrate():
    """Add new fields to reports and observations tables"""
    
    migrations = [
        # Reports table - add extraction metadata
        """
        ALTER TABLE reports 
        ADD COLUMN IF NOT EXISTS extraction_method VARCHAR,
        ADD COLUMN IF NOT EXISTS page_stats JSONB;
        """,
        
        # Observations table - add lab parsing fields
        """
        ALTER TABLE observations 
        ADD COLUMN IF NOT EXISTS display_name VARCHAR,
        ADD COLUMN IF NOT EXISTS flag VARCHAR,
        ADD COLUMN IF NOT EXISTS raw_line TEXT,
        ADD COLUMN IF NOT EXISTS page_num INTEGER;
        """,
        
        # Create index on extraction_method for filtering
        """
        CREATE INDEX IF NOT EXISTS idx_reports_extraction_method 
        ON reports(extraction_method);
        """,
    ]
    
    async for db in get_db():
        for migration_sql in migrations:
            try:
                await db.execute(text(migration_sql))
                await db.commit()
                print(f"✓ Migration executed successfully")
            except Exception as e:
                print(f"Migration note: {e}")
                await db.rollback()
        break


if __name__ == "__main__":
    print("Running database migrations...")
    asyncio.run(migrate())
    print("Migrations complete!")
