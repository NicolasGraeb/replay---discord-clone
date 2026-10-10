import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.server_member import MemberRole, ServerMember


class ServerMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID, server_id: uuid.UUID) -> Optional[ServerMember]:
        result = await self.session.execute(
            select(ServerMember).where(
                ServerMember.user_id == user_id,
                ServerMember.server_id == server_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_server_members(self, server_id: uuid.UUID) -> List[ServerMember]:
        result = await self.session.execute(
            select(ServerMember).where(ServerMember.server_id == server_id)
        )
        return list(result.scalars().all())

    async def get_user_servers(self, user_id: uuid.UUID) -> List[ServerMember]:
        result = await self.session.execute(
            select(ServerMember).where(ServerMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(self, member: ServerMember) -> ServerMember:
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def save(self, member: ServerMember) -> ServerMember:
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def delete(self, member: ServerMember) -> None:
        await self.session.delete(member)
        await self.session.commit()
