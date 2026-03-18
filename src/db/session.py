"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings

settings = get_settings()

# Create async engine
# Configure connection pool settings (SQLite doesn't support these)
# Configure connection pool settings (SQLite doesn't support these)
engine_kwargs = {"echo": False}
if "sqlite" not in str(settings.database_url):
    engine_kwargs["pool_size"] = settings.database_pool_size
    engine_kwargs["max_overflow"] = settings.database_max_overflow
elif ":memory:" in str(settings.database_url):
    from sqlalchemy.pool import StaticPool
    engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(settings.database_url, **engine_kwargs)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


from src.models.database import Base

async def init_db() -> None:
    """Initialize database tables."""
    if "sqlite" in str(settings.database_url):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        # In production, use Alembic migrations instead
        pass
