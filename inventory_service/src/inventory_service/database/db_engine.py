from typing import Any, AsyncGenerator, Final

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from inventory_service.core.core import DATABASE_URL

engine: Final = create_async_engine(DATABASE_URL)


async def init_db() -> None:
    """Init database"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """Generate database session"""
    async with AsyncSession(engine) as session:
        yield session
