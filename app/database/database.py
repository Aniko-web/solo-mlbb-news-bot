import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from app.config.settings import get_settings
from app.database.models import Base
from app.utils.logger import logger

settings = get_settings()

# Ensure SQLite directory exists if local file path
if "sqlite" in settings.DATABASE_URL:
    db_file_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_file_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


from sqlalchemy import text


async def init_db() -> None:
    """Initialize database tables and ensure column migrations."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Ensure new notification flags exist in existing databases
            for col_name in ["upcoming_notified", "result_notified"]:
                try:
                    await conn.execute(text(f"ALTER TABLE matches ADD COLUMN {col_name} BOOLEAN DEFAULT 0"))
                except Exception:
                    pass
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
