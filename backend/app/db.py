import asyncio
from pathlib import Path
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.settings import settings

# Use connection pooling with proper settings for async PostgreSQL
engine = create_async_engine(
    settings.database_url, 
    echo=False,
    pool_size=5,  # Keep a small pool
    max_overflow=10,  # Allow some overflow
    pool_pre_ping=True,  # Verify connections are alive before use
    pool_recycle=300,  # Recycle connections after 5 minutes
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# For backwards compatibility - also export as async_session
async_session = async_session_maker

Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def run_migrations() -> None:
    """
    Run Alembic migrations to `head` (best for dev/local).
    Uses the sync driver path configured in `backend/alembic/env.py`.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"
    cfg = Config(str(alembic_ini))

    await asyncio.to_thread(command.upgrade, cfg, "head")

async def init_db():
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting database initialization...")
    
    # Import all models to ensure they're registered with Base.metadata
    # This is critical for ORM queries to work properly
    try:
        logger.info("Importing models...")
        from app import models  # noqa: F401
        logger.info(f"Models imported successfully. {len(Base.metadata.tables)} tables registered")
    except Exception as e:
        logger.error(f"Could not import models: {e}", exc_info=True)
        raise
    
    try:
        if settings.AUTO_MIGRATE:
            logger.info("Running Alembic migrations...")
            await run_migrations()
            logger.info("Migrations completed successfully")
            return

        # Create tables (with checkfirst=True to only create missing ones)
        # Using a short timeout to avoid hanging on existing tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await asyncio.wait_for(
                conn.run_sync(Base.metadata.create_all, checkfirst=True),
                timeout=10.0
            )
        logger.info("Database tables created successfully")
        logger.info("Database initialization complete")
    except asyncio.TimeoutError:
        logger.warning("Table creation timed out - assuming tables already exist")
        logger.info("Database initialization complete (with timeout)")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise Exception(f"Database initialization failed: {e}")
