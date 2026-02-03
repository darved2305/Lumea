"""
Quick seed script for medicines catalog - creates table if needed and seeds data
"""
import asyncio
import asyncpg
import os
from uuid import uuid4

# Parse database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://neondb_owner:npg_hWF9zPurf2OS@ep-twilight-resonance-ah9o88p9-pooler.c-3.us-east-1.aws.neon.tech/neondb?ssl=require")

# Convert to asyncpg format
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Medicines data
MEDICINES = [
    ("Paracetamol IP 500mg", "Paracetamol", "500mg", "tablet", None, 6.80, "PMBI", "PMBI Jan Aushadhi", True),
    ("Paracetamol IP 650mg", "Paracetamol", "650mg", "tablet", None, 8.50, "PMBI", "PMBI Jan Aushadhi", True),
    ("Metformin Hydrochloride IP 500mg", "Metformin", "500mg", "tablet", None, 12.50, "PMBI", "PMBI Jan Aushadhi", True),
    ("Metformin Hydrochloride IP 500mg SR", "Metformin", "500mg", "tablet", "SR", 15.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Metformin Hydrochloride IP 850mg", "Metformin", "850mg", "tablet", None, 18.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Atorvastatin IP 10mg", "Atorvastatin", "10mg", "tablet", None, 25.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Atorvastatin IP 20mg", "Atorvastatin", "20mg", "tablet", None, 35.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Amlodipine IP 5mg", "Amlodipine", "5mg", "tablet", None, 8.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Amlodipine IP 10mg", "Amlodipine", "10mg", "tablet", None, 12.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Losartan Potassium IP 50mg", "Losartan", "50mg", "tablet", None, 22.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Telmisartan IP 40mg", "Telmisartan", "40mg", "tablet", None, 25.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Omeprazole IP 20mg", "Omeprazole", "20mg", "capsule", None, 12.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Pantoprazole IP 40mg", "Pantoprazole", "40mg", "tablet", None, 18.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Cetirizine IP 10mg", "Cetirizine", "10mg", "tablet", None, 5.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Azithromycin IP 500mg", "Azithromycin", "500mg", "tablet", None, 65.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Ciprofloxacin IP 500mg", "Ciprofloxacin", "500mg", "tablet", None, 28.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Ibuprofen IP 400mg", "Ibuprofen", "400mg", "tablet", None, 12.00, "PMBI", "PMBI Jan Aushadhi", True),
    ("Aspirin IP 75mg", "Aspirin", "75mg", "tablet", None, 5.00, "PMBI", "PMBI Jan Aushadhi", True),
    # Generic alternatives
    ("Metformin 500mg Tab", "Metformin", "500mg", "tablet", None, 25.00, "Generic Pharma", "Generic", False),
    ("Metformin 500mg SR Tab", "Metformin", "500mg", "tablet", "SR", 35.00, "Generic Pharma", "Generic", False),
    ("Atorvastatin 10mg Tab", "Atorvastatin", "10mg", "tablet", None, 55.00, "Generic Pharma", "Generic", False),
    ("Atorvastatin 20mg Tab", "Atorvastatin", "20mg", "tablet", None, 85.00, "Generic Pharma", "Generic", False),
    ("Paracetamol 500mg Tab", "Paracetamol", "500mg", "tablet", None, 15.00, "Generic Pharma", "Generic", False),
    ("Paracetamol 650mg Tab", "Paracetamol", "650mg", "tablet", None, 22.00, "Generic Pharma", "Generic", False),
]

async def seed():
    """Seed the database."""
    print(f"Connecting to database...")
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Create table if not exists
        print("Creating table if not exists...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS generic_catalog (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_name VARCHAR(500) NOT NULL,
                salt VARCHAR(500) NOT NULL,
                strength VARCHAR(100) NOT NULL,
                form VARCHAR(100) NOT NULL,
                release_type VARCHAR(50),
                mrp NUMERIC(10, 2),
                manufacturer VARCHAR(300),
                source VARCHAR(50) NOT NULL DEFAULT 'jan_aushadhi',
                is_jan_aushadhi BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Create indexes
        print("Creating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_generic_catalog_salt ON generic_catalog(salt)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_generic_catalog_salt_strength_form 
            ON generic_catalog(salt, strength, form)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_generic_catalog_product_name 
            ON generic_catalog(product_name)
        """)
        
        # Check if already seeded
        count = await conn.fetchval("SELECT COUNT(*) FROM generic_catalog")
        if count > 0:
            print(f"Table already has {count} entries. Skipping seed.")
            return
        
        # Insert data
        print(f"Inserting {len(MEDICINES)} medicines...")
        for med in MEDICINES:
            product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan = med
            await conn.execute("""
                INSERT INTO generic_catalog 
                (id, product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan_aushadhi)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, str(uuid4()), product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan)
        
        final_count = await conn.fetchval("SELECT COUNT(*) FROM generic_catalog")
        print(f"✅ Seeded successfully! Total medicines: {final_count}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
