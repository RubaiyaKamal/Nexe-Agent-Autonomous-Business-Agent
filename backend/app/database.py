from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# Pooled engine for FastAPI (long-lived process, single event loop)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def celery_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh NullPool engine per call — safe inside asyncio.run() in Celery tasks."""
    _engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with AsyncSession(_engine, expire_on_commit=False) as session:
            yield session
    finally:
        await _engine.dispose()
