import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from core.media_s3 import signed_image_url
from models.user import User


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=60)
    avatar_url: Optional[str] = Field(default=None, max_length=500)


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    avatar_url: Optional[str] = None
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


def _display_avatar(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return signed_image_url(s) or s


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=_display_avatar(user.avatar_url),
        created_at=user.created_at,
    )
