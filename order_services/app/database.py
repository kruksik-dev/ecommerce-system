import os
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@order-db:5432/order_db"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[Any, Any]:
    async with async_session() as session:
        yield session
