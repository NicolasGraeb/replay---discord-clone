import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.channel import Channel
    from models.user import User


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_channel_created", "channel_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    author: Mapped["User"] = relationship("User", back_populates="messages")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="messages")
