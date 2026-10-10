import uuid
from datetime import datetime, timezone
from typing import List, Optional

from models.message import Message
from repositories.message_repository import MessageRepository
from schemas.message import MessageCreate, MessageUpdate


class MessageService:
    def __init__(self, repo: MessageRepository) -> None:
        self.repo = repo

    async def send_message(
        self,
        author_id: uuid.UUID,
        channel_id: uuid.UUID,
        data: MessageCreate,
    ) -> Message:
        message = Message(
            content=data.content,
            author_id=author_id,
            channel_id=channel_id,
        )
        created = await self.repo.create(message)
        loaded = await self.repo.get_by_id_with_author(created.id)
        return loaded or created

    async def send_message_with_image(
        self,
        author_id: uuid.UUID,
        channel_id: uuid.UUID,
        content: str,
        image_key: str,
    ) -> Message:
        message = Message(
            content=content,
            author_id=author_id,
            channel_id=channel_id,
            image_key=image_key,
        )
        created = await self.repo.create(message)
        loaded = await self.repo.get_by_id_with_author(created.id)
        return loaded or created

    async def get_channel_messages(
        self,
        channel_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        return await self.repo.get_by_channel(channel_id, limit=limit, offset=offset)

    async def get_message(self, message_id: uuid.UUID) -> Optional[Message]:
        return await self.repo.get_by_id(message_id)

    async def update_message(
        self, message: Message, data: MessageUpdate, requestor_id: uuid.UUID
    ) -> Message:
        if message.author_id != requestor_id:
            raise PermissionError("Cannot edit another user's message")
        message.content = data.content
        message.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        saved = await self.repo.save(message)
        loaded = await self.repo.get_by_id_with_author(saved.id)
        return loaded or saved

    async def delete_message(
        self, message: Message, requestor_id: uuid.UUID
    ) -> None:
        if message.author_id != requestor_id:
            raise PermissionError("Cannot delete another user's message")
        await self.repo.delete(message)
