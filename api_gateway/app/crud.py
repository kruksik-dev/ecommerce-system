from typing import Sequence

from database import async_session
from sqlalchemy.future import select
from tables import User


async def get_all_users() -> Sequence[User]:
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return users


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        return user
