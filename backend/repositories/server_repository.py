import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.server import Server
from models.server_member import ServerMember
from repositories.base import BaseRepository


class ServerRepository(BaseRepository[Server]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Server, session)

    async def get_by_owner(self, owner_id: uuid.UUID) -> List[Server]:
        result = await self.session.execute(
            select(Server).where(Server.owner_id == owner_id)
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: uuid.UUID) -> List[Server]:
        result = await self.session.execute(
            select(Server)
            .join(ServerMember, ServerMember.server_id == Server.id)
            .where(ServerMember.user_id == user_id)
            .order_by(Server.created_at.desc())
        )
        return list(result.scalars().all())
