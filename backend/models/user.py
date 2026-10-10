import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.message import Message
    from models.refresh_token import RefreshToken
    from models.server import Server
    from models.server_member import ServerMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(90), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    owned_servers: Mapped[List["Server"]] = relationship(
        "Server",
        back_populates="owner",
        foreign_keys="Server.owner_id",
    )
    server_memberships: Mapped[List["ServerMember"]] = relationship(
        "ServerMember", back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="author", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
