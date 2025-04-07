import os
from typing import Any, AsyncGenerator, Final

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

DATABASE_URL: Final = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@postgres:5432/inventory_db"
)
engine: Final = create_async_engine(DATABASE_URL)


async def init_db() -> None:
    """Init database"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """Generate database session"""
    async with AsyncSession(engine) as session:
        yield session
