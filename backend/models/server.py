import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.channel import Channel
    from models.server_member import ServerMember
    from models.user import User


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_servers",
        foreign_keys=[owner_id],
    )
    members: Mapped[List["ServerMember"]] = relationship(
        "ServerMember", back_populates="server", cascade="all, delete-orphan"
    )
    channels: Mapped[List["Channel"]] = relationship(
        "Channel", back_populates="server", cascade="all, delete-orphan"
    )
