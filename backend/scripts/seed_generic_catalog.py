"""
Seed Generic Medicine Catalog

This script populates the generic_catalog table with medicine data.
Can be extended to load data from:
- Jan Aushadhi Product List (PMBI)
- CDSCO Generic Medicine List
- Custom CSV files

Usage:
    python -m scripts.seed_generic_catalog
    
Or within Docker:
    docker exec -it ggw-backend python -m scripts.seed_generic_catalog
"""
import asyncio
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4

# Setup Django-style imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Jan Aushadhi medicines data
# In production, load from official PMBI CSV
SAMPLE_JAN_AUSHADHI_DATA = [
    # Format: (product_name, salt, strength, form, release_type, mrp, manufacturer)
    ("Paracetamol IP 500mg", "Paracetamol", "500mg", "tablet", None, 6.80, "PMBI"),
    ("Paracetamol IP 650mg", "Paracetamol", "650mg", "tablet", None, 8.50, "PMBI"),
    ("Metformin Hydrochloride IP 500mg", "Metformin", "500mg", "tablet", None, 12.50, "PMBI"),
    ("Metformin Hydrochloride IP 500mg SR", "Metformin", "500mg", "tablet", "SR", 15.00, "PMBI"),
    ("Metformin Hydrochloride IP 850mg", "Metformin", "850mg", "tablet", None, 18.00, "PMBI"),
    ("Metformin Hydrochloride IP 1000mg SR", "Metformin", "1000mg", "tablet", "SR", 22.00, "PMBI"),
    ("Atorvastatin IP 10mg", "Atorvastatin", "10mg", "tablet", None, 25.00, "PMBI"),
    ("Atorvastatin IP 20mg", "Atorvastatin", "20mg", "tablet", None, 35.00, "PMBI"),
    ("Atorvastatin IP 40mg", "Atorvastatin", "40mg", "tablet", None, 48.00, "PMBI"),
    ("Amlodipine IP 5mg", "Amlodipine", "5mg", "tablet", None, 8.00, "PMBI"),
    ("Amlodipine IP 10mg", "Amlodipine", "10mg", "tablet", None, 12.00, "PMBI"),
    ("Losartan Potassium IP 25mg", "Losartan", "25mg", "tablet", None, 15.00, "PMBI"),
    ("Losartan Potassium IP 50mg", "Losartan", "50mg", "tablet", None, 22.00, "PMBI"),
    ("Losartan Potassium IP 100mg", "Losartan", "100mg", "tablet", None, 35.00, "PMBI"),
    ("Telmisartan IP 20mg", "Telmisartan", "20mg", "tablet", None, 18.00, "PMBI"),
    ("Telmisartan IP 40mg", "Telmisartan", "40mg", "tablet", None, 25.00, "PMBI"),
    ("Telmisartan IP 80mg", "Telmisartan", "80mg", "tablet", None, 38.00, "PMBI"),
    ("Omeprazole IP 20mg", "Omeprazole", "20mg", "capsule", None, 12.00, "PMBI"),
    ("Pantoprazole IP 40mg", "Pantoprazole", "40mg", "tablet", None, 18.00, "PMBI"),
    ("Rabeprazole IP 20mg", "Rabeprazole", "20mg", "tablet", None, 22.00, "PMBI"),
    ("Cetirizine IP 10mg", "Cetirizine", "10mg", "tablet", None, 5.00, "PMBI"),
    ("Levocetirizine IP 5mg", "Levocetirizine", "5mg", "tablet", None, 8.00, "PMBI"),
    ("Azithromycin IP 250mg", "Azithromycin", "250mg", "tablet", None, 45.00, "PMBI"),
    ("Azithromycin IP 500mg", "Azithromycin", "500mg", "tablet", None, 65.00, "PMBI"),
    ("Amoxicillin IP 250mg", "Amoxicillin", "250mg", "capsule", None, 15.00, "PMBI"),
    ("Amoxicillin IP 500mg", "Amoxicillin", "500mg", "capsule", None, 25.00, "PMBI"),
    ("Ciprofloxacin IP 250mg", "Ciprofloxacin", "250mg", "tablet", None, 18.00, "PMBI"),
    ("Ciprofloxacin IP 500mg", "Ciprofloxacin", "500mg", "tablet", None, 28.00, "PMBI"),
    ("Ibuprofen IP 200mg", "Ibuprofen", "200mg", "tablet", None, 8.00, "PMBI"),
    ("Ibuprofen IP 400mg", "Ibuprofen", "400mg", "tablet", None, 12.00, "PMBI"),
    ("Diclofenac Sodium IP 50mg", "Diclofenac", "50mg", "tablet", None, 10.00, "PMBI"),
    ("Aspirin IP 75mg", "Aspirin", "75mg", "tablet", None, 5.00, "PMBI"),
    ("Aspirin IP 150mg", "Aspirin", "150mg", "tablet", None, 8.00, "PMBI"),
    ("Clopidogrel IP 75mg", "Clopidogrel", "75mg", "tablet", None, 18.00, "PMBI"),
    ("Rosuvastatin IP 5mg", "Rosuvastatin", "5mg", "tablet", None, 22.00, "PMBI"),
    ("Rosuvastatin IP 10mg", "Rosuvastatin", "10mg", "tablet", None, 32.00, "PMBI"),
    ("Rosuvastatin IP 20mg", "Rosuvastatin", "20mg", "tablet", None, 45.00, "PMBI"),
    ("Glimepiride IP 1mg", "Glimepiride", "1mg", "tablet", None, 15.00, "PMBI"),
    ("Glimepiride IP 2mg", "Glimepiride", "2mg", "tablet", None, 22.00, "PMBI"),
    ("Gliclazide IP 40mg", "Gliclazide", "40mg", "tablet", None, 18.00, "PMBI"),
    ("Gliclazide IP 80mg", "Gliclazide", "80mg", "tablet", None, 28.00, "PMBI"),
    ("Sitagliptin IP 50mg", "Sitagliptin", "50mg", "tablet", None, 85.00, "PMBI"),
    ("Sitagliptin IP 100mg", "Sitagliptin", "100mg", "tablet", None, 120.00, "PMBI"),
    ("Vildagliptin IP 50mg", "Vildagliptin", "50mg", "tablet", None, 75.00, "PMBI"),
    ("Empagliflozin IP 10mg", "Empagliflozin", "10mg", "tablet", None, 95.00, "PMBI"),
    ("Empagliflozin IP 25mg", "Empagliflozin", "25mg", "tablet", None, 130.00, "PMBI"),
    ("Dapagliflozin IP 5mg", "Dapagliflozin", "5mg", "tablet", None, 88.00, "PMBI"),
    ("Dapagliflozin IP 10mg", "Dapagliflozin", "10mg", "tablet", None, 115.00, "PMBI"),
    ("Linagliptin IP 5mg", "Linagliptin", "5mg", "tablet", None, 145.00, "PMBI"),
    ("Ramipril IP 2.5mg", "Ramipril", "2.5mg", "tablet", None, 12.00, "PMBI"),
    ("Ramipril IP 5mg", "Ramipril", "5mg", "tablet", None, 18.00, "PMBI"),
    ("Enalapril IP 2.5mg", "Enalapril", "2.5mg", "tablet", None, 10.00, "PMBI"),
    ("Enalapril IP 5mg", "Enalapril", "5mg", "tablet", None, 15.00, "PMBI"),
    ("Bisoprolol IP 2.5mg", "Bisoprolol", "2.5mg", "tablet", None, 12.00, "PMBI"),
    ("Bisoprolol IP 5mg", "Bisoprolol", "5mg", "tablet", None, 18.00, "PMBI"),
    ("Metoprolol Succinate IP 25mg XL", "Metoprolol", "25mg", "tablet", "XL", 22.00, "PMBI"),
    ("Metoprolol Succinate IP 50mg XL", "Metoprolol", "50mg", "tablet", "XL", 32.00, "PMBI"),
    ("Nebivolol IP 2.5mg", "Nebivolol", "2.5mg", "tablet", None, 25.00, "PMBI"),
    ("Nebivolol IP 5mg", "Nebivolol", "5mg", "tablet", None, 38.00, "PMBI"),
    ("Hydrochlorothiazide IP 12.5mg", "Hydrochlorothiazide", "12.5mg", "tablet", None, 8.00, "PMBI"),
    ("Hydrochlorothiazide IP 25mg", "Hydrochlorothiazide", "25mg", "tablet", None, 12.00, "PMBI"),
    ("Furosemide IP 40mg", "Furosemide", "40mg", "tablet", None, 10.00, "PMBI"),
    ("Spironolactone IP 25mg", "Spironolactone", "25mg", "tablet", None, 18.00, "PMBI"),
    ("Spironolactone IP 50mg", "Spironolactone", "50mg", "tablet", None, 28.00, "PMBI"),
    ("Montelukast IP 10mg", "Montelukast", "10mg", "tablet", None, 35.00, "PMBI"),
    ("Salbutamol IP 2mg", "Salbutamol", "2mg", "tablet", None, 8.00, "PMBI"),
    ("Salbutamol IP 4mg", "Salbutamol", "4mg", "tablet", None, 12.00, "PMBI"),
    ("Levothyroxine Sodium IP 25mcg", "Levothyroxine", "25mcg", "tablet", None, 15.00, "PMBI"),
    ("Levothyroxine Sodium IP 50mcg", "Levothyroxine", "50mcg", "tablet", None, 18.00, "PMBI"),
    ("Levothyroxine Sodium IP 100mcg", "Levothyroxine", "100mcg", "tablet", None, 22.00, "PMBI"),
    ("Calcium Carbonate IP 500mg + Vitamin D3 250IU", "Calcium+Vitamin D3", "500mg+250IU", "tablet", None, 12.00, "PMBI"),
    ("Folic Acid IP 5mg", "Folic Acid", "5mg", "tablet", None, 8.00, "PMBI"),
    ("Ferrous Sulfate IP 200mg", "Ferrous Sulfate", "200mg", "tablet", None, 10.00, "PMBI"),
    ("Vitamin B Complex", "Vitamin B Complex", "", "tablet", None, 15.00, "PMBI"),
    ("Multivitamin Tablets", "Multivitamin", "", "tablet", None, 18.00, "PMBI"),
]

# Common generic alternatives (non-Jan-Aushadhi)
GENERIC_ALTERNATIVES = [
    ("Metformin 500mg Tab", "Metformin", "500mg", "tablet", None, 25.00, "Generic Pharma"),
    ("Metformin 500mg SR Tab", "Metformin", "500mg", "tablet", "SR", 35.00, "Generic Pharma"),
    ("Metformin 850mg Tab", "Metformin", "850mg", "tablet", None, 38.00, "Generic Pharma"),
    ("Atorvastatin 10mg Tab", "Atorvastatin", "10mg", "tablet", None, 55.00, "Generic Pharma"),
    ("Atorvastatin 20mg Tab", "Atorvastatin", "20mg", "tablet", None, 85.00, "Generic Pharma"),
    ("Amlodipine 5mg Tab", "Amlodipine", "5mg", "tablet", None, 22.00, "Generic Pharma"),
    ("Losartan 50mg Tab", "Losartan", "50mg", "tablet", None, 48.00, "Generic Pharma"),
    ("Telmisartan 40mg Tab", "Telmisartan", "40mg", "tablet", None, 55.00, "Generic Pharma"),
    ("Pantoprazole 40mg Tab", "Pantoprazole", "40mg", "tablet", None, 38.00, "Generic Pharma"),
    ("Cetirizine 10mg Tab", "Cetirizine", "10mg", "tablet", None, 12.00, "Generic Pharma"),
    ("Azithromycin 500mg Tab", "Azithromycin", "500mg", "tablet", None, 125.00, "Generic Pharma"),
    ("Paracetamol 500mg Tab", "Paracetamol", "500mg", "tablet", None, 15.00, "Generic Pharma"),
    ("Paracetamol 650mg Tab", "Paracetamol", "650mg", "tablet", None, 22.00, "Generic Pharma"),
]


async def seed_database(database_url: str):
    """Seed the generic_catalog table with medicine data."""
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if table exists and has data
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM generic_catalog"))
            count = result.scalar()
            if count > 0:
                logger.info(f"generic_catalog already has {count} entries. Skipping seed.")
                logger.info("To re-seed, truncate the table first: TRUNCATE generic_catalog;")
                return
        except Exception as e:
            logger.error(f"Table check failed: {e}")
            logger.info("Make sure to run database migrations first!")
            return
        
        # Insert Jan Aushadhi data
        logger.info("Seeding Jan Aushadhi medicines...")
        for item in SAMPLE_JAN_AUSHADHI_DATA:
            product_name, salt, strength, form, release_type, mrp, manufacturer = item
            await session.execute(
                text("""
                    INSERT INTO generic_catalog 
                    (id, product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan_aushadhi, created_at)
                    VALUES (:id, :product_name, :salt, :strength, :form, :release_type, :mrp, :manufacturer, :source, :is_jan_aushadhi, NOW())
                """),
                {
                    "id": str(uuid4()),
                    "product_name": product_name,
                    "salt": salt,
                    "strength": strength,
                    "form": form,
                    "release_type": release_type,
                    "mrp": mrp,
                    "manufacturer": manufacturer,
                    "source": "PMBI Jan Aushadhi",
                    "is_jan_aushadhi": True
                }
            )
        
        # Insert generic alternatives
        logger.info("Seeding generic alternatives...")
        for item in GENERIC_ALTERNATIVES:
            product_name, salt, strength, form, release_type, mrp, manufacturer = item
            await session.execute(
                text("""
                    INSERT INTO generic_catalog 
                    (id, product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan_aushadhi, created_at)
                    VALUES (:id, :product_name, :salt, :strength, :form, :release_type, :mrp, :manufacturer, :source, :is_jan_aushadhi, NOW())
                """),
                {
                    "id": str(uuid4()),
                    "product_name": product_name,
                    "salt": salt,
                    "strength": strength,
                    "form": form,
                    "release_type": release_type,
                    "mrp": mrp,
                    "manufacturer": manufacturer,
                    "source": "Generic",
                    "is_jan_aushadhi": False
                }
            )
        
        await session.commit()
        
        # Verify
        result = await session.execute(text("SELECT COUNT(*) FROM generic_catalog"))
        count = result.scalar()
        logger.info(f"Successfully seeded {count} medicines to generic_catalog!")


async def seed_from_csv(database_url: str, csv_path: str):
    """
    Seed from a CSV file.
    
    Expected CSV columns:
    product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan_aushadhi
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO generic_catalog 
                            (id, product_name, salt, strength, form, release_type, mrp, manufacturer, source, is_jan_aushadhi, created_at)
                            VALUES (:id, :product_name, :salt, :strength, :form, :release_type, :mrp, :manufacturer, :source, :is_jan_aushadhi, NOW())
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": str(uuid4()),
                            "product_name": row.get('product_name', ''),
                            "salt": row.get('salt', ''),
                            "strength": row.get('strength', ''),
                            "form": row.get('form', 'tablet'),
                            "release_type": row.get('release_type') or None,
                            "mrp": float(row.get('mrp', 0)) if row.get('mrp') else None,
                            "manufacturer": row.get('manufacturer', ''),
                            "source": row.get('source', 'CSV Import'),
                            "is_jan_aushadhi": row.get('is_jan_aushadhi', '').lower() in ('true', '1', 'yes')
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Error inserting row: {row}, error: {e}")
            
            await session.commit()
            logger.info(f"Imported {count} medicines from CSV")


if __name__ == "__main__":
    import os
    
    # Get database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://ggw:ggwpassword@localhost:5432/ggwdb"
    )
    
    # Check for CSV argument
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        logger.info(f"Seeding from CSV: {csv_path}")
        asyncio.run(seed_from_csv(database_url, csv_path))
    else:
        logger.info("Seeding with sample data...")
        asyncio.run(seed_database(database_url))
