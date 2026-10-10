import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.server import Server
    from models.user import User


class MemberRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"


class ServerMember(Base):
    __tablename__ = "server_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("servers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[MemberRole] = mapped_column(
        SAEnum(MemberRole, name="memberrole"), nullable=False, default=MemberRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="server_memberships")
    server: Mapped["Server"] = relationship("Server", back_populates="members")
