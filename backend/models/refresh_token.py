import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.user import User


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True  # id == jti from JWT
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
