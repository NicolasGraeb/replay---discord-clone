import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[uuid.UUID]) -> Dict[uuid.UUID, User]:
        if not ids:
            return {}
        result = await self.session.execute(select(User).where(User.id.in_(ids)))
        rows = list(result.scalars().all())
        return {u.id: u for u in rows}
