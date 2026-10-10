import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.channel import ChannelType


class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: ChannelType = ChannelType.TEXT


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ChannelResponse(BaseModel):
    id: uuid.UUID
    name: str
    server_id: uuid.UUID
    type: ChannelType
    created_at: datetime

    model_config = {"from_attributes": True}


class VoiceParticipantResponse(BaseModel):
    user_id: str
    username: str
