import enum
import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.message import Message
    from models.server import Server


class ChannelType(str, enum.Enum):
    TEXT = "TEXT"
    VOICE = "VOICE"


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ChannelType] = mapped_column(
        SAEnum(ChannelType, name="channeltype"),
        nullable=False,
        default=ChannelType.TEXT,
    )

    server: Mapped["Server"] = relationship("Server", back_populates="channels")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="channel", cascade="all, delete-orphan"
    )
