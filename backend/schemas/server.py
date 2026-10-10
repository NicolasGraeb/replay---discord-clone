import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.server_member import MemberRole


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon_url: Optional[str] = Field(default=None, max_length=500)


class ServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icon_url: Optional[str] = Field(default=None, max_length=500)


class ServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    icon_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ServerMemberResponse(BaseModel):
    user_id: uuid.UUID
    server_id: uuid.UUID
    role: MemberRole
    joined_at: datetime
    username: Optional[str] = None

    model_config = {"from_attributes": True}


class UpdateMemberRole(BaseModel):
    role: MemberRole
