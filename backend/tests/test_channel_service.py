import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.channel import Channel, ChannelType
from schemas.channel import ChannelCreate, ChannelUpdate
from services.channel_service import ChannelService


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(repo: MagicMock) -> ChannelService:
    return ChannelService(repo)


@pytest.mark.asyncio
async def test_create_channel(service: ChannelService, repo: MagicMock):
    sid = uuid.uuid4()
    data = ChannelCreate(name="general", type=ChannelType.TEXT)
    ch = Channel(name=data.name, server_id=sid, type=data.type)
    ch.id = uuid.uuid4()
    repo.create = AsyncMock(return_value=ch)

    out = await service.create_channel(sid, data)

    assert out is ch
    repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_channel_delegates(service: ChannelService, repo: MagicMock):
    cid = uuid.uuid4()
    repo.get_by_id = AsyncMock(return_value=None)
    assert await service.get_channel(cid) is None
    repo.get_by_id.assert_awaited_once_with(cid)


@pytest.mark.asyncio
async def test_get_server_channels(service: ChannelService, repo: MagicMock):
    sid = uuid.uuid4()
    repo.get_by_server = AsyncMock(return_value=[])
    assert await service.get_server_channels(sid) == []
    repo.get_by_server.assert_awaited_once_with(sid)


@pytest.mark.asyncio
async def test_update_channel_applies_name(service: ChannelService, repo: MagicMock):
    ch = Channel(name="old", server_id=uuid.uuid4(), type=ChannelType.TEXT)
    ch.id = uuid.uuid4()
    repo.save = AsyncMock(side_effect=lambda c: c)

    out = await service.update_channel(ch, ChannelUpdate(name="new-name"))

    assert out.name == "new-name"
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_channel(service: ChannelService, repo: MagicMock):
    ch = MagicMock(spec=Channel)
    repo.delete = AsyncMock(return_value=None)
    await service.delete_channel(ch)
    repo.delete.assert_awaited_once_with(ch)
