import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.settings import settings

# Use NullPool for async to avoid connection pool exhaustion issues
# Each request gets a fresh connection that's returned immediately after use
engine = create_async_engine(
    settings.database_url, 
    echo=False,
    pool_pre_ping=True,  # Verify connections are alive before use
    pool_size=20,        # Increase base pool size
    max_overflow=40,     # Allow more overflow connections
    pool_timeout=60,     # Wait longer before timeout
    pool_recycle=1800,   # Recycle connections after 30 minutes
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
    if settings.AUTO_MIGRATE:
        # Prefer migrations; create_all() does not add columns to existing tables.
        await run_migrations()
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
