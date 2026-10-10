import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.message import Message
from repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Message, session)

    async def get_by_id_with_author(self, message_id: uuid.UUID) -> Optional[Message]:
        result = await self.session.execute(
            select(Message)
            .options(joinedload(Message.author))
            .where(Message.id == message_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_channel(
        self, channel_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Message]:
        result = await self.session.execute(
            select(Message)
            .options(joinedload(Message.author))
            .where(Message.channel_id == channel_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.unique().scalars().all())
