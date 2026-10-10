import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import Channel
from repositories.base import BaseRepository


class ChannelRepository(BaseRepository[Channel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Channel, session)

    async def get_by_server(self, server_id: uuid.UUID) -> List[Channel]:
        result = await self.session.execute(
            select(Channel)
            .where(Channel.server_id == server_id)
            .order_by(Channel.created_at.asc())
        )
        return list(result.scalars().all())
