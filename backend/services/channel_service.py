import uuid
from typing import List, Optional

from models.channel import Channel
from repositories.channel_repository import ChannelRepository
from schemas.channel import ChannelCreate, ChannelUpdate


class ChannelService:
    def __init__(self, repo: ChannelRepository) -> None:
        self.repo = repo

    async def create_channel(self, server_id: uuid.UUID, data: ChannelCreate) -> Channel:
        channel = Channel(name=data.name, server_id=server_id, type=data.type)
        return await self.repo.create(channel)

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[Channel]:
        return await self.repo.get_by_id(channel_id)

    async def get_server_channels(self, server_id: uuid.UUID) -> List[Channel]:
        return await self.repo.get_by_server(server_id)

    async def update_channel(self, channel: Channel, data: ChannelUpdate) -> Channel:
        if data.name is not None:
            channel.name = data.name
        return await self.repo.save(channel)

    async def delete_channel(self, channel: Channel) -> None:
        await self.repo.delete(channel)
