"""
Database migration to add missing columns to reports and observations tables.
Run this to update schema after model changes.
"""
import asyncio
from sqlalchemy import text
from app.db import engine

async def run_migration():
    print("Adding missing columns to database tables...")
    
    async with engine.begin() as conn:
        # Add missing columns to reports table
        reports_columns = [
            ("extraction_method", "VARCHAR(50)"),
            ("page_stats", "JSONB"),
            ("extracted_data", "JSONB"),
        ]
        
        for col_name, col_type in reports_columns:
            try:
                await conn.execute(text(f"""
                    ALTER TABLE reports 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                print(f"  ✅ Added reports.{col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⏭️  reports.{col_name} already exists")
                else:
                    print(f"  ❌ Failed to add reports.{col_name}: {e}")
        
        # Add missing columns to observations table
        observations_columns = [
            ("display_name", "VARCHAR(255)"),
            ("flag", "VARCHAR(50)"),
            ("raw_line", "TEXT"),
            ("page_num", "INTEGER"),
        ]
        
        for col_name, col_type in observations_columns:
            try:
                await conn.execute(text(f"""
                    ALTER TABLE observations 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                print(f"  ✅ Added observations.{col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⏭️  observations.{col_name} already exists")
                else:
                    print(f"  ❌ Failed to add observations.{col_name}: {e}")
    
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    asyncio.run(run_migration())
