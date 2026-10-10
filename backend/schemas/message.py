import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from core.media_s3 import signed_image_url
from models.message import Message
from schemas.user import _display_avatar


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    content: str
    author_id: uuid.UUID
    channel_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    author_username: str
    author_avatar_url: Optional[str] = None
    image_url: Optional[str] = None


def message_to_response(message: Message) -> MessageResponse:
    author = getattr(message, "author", None)
    username = author.username if author is not None else "?"
    raw_avatar = author.avatar_url if author is not None else None
    key = getattr(message, "image_key", None)
    return MessageResponse(
        id=message.id,
        content=message.content,
        author_id=message.author_id,
        channel_id=message.channel_id,
        created_at=message.created_at,
        updated_at=message.updated_at,
        author_username=username,
        author_avatar_url=_display_avatar(raw_avatar),
        image_url=signed_image_url(key),
    )


def message_realtime_payload(dto: MessageResponse) -> dict:
    """Ten sam kształt co broadcast z `ws/channel_ws.py` (klient `useChannelMessages`)."""
    return {
        "id": str(dto.id),
        "content": dto.content,
        "author_id": str(dto.author_id),
        "author_username": dto.author_username,
        "author_avatar_url": dto.author_avatar_url,
        "channel_id": str(dto.channel_id),
        "created_at": dto.created_at.isoformat(),
        "updated_at": dto.updated_at.isoformat() if dto.updated_at else None,
        "image_url": dto.image_url,
    }
