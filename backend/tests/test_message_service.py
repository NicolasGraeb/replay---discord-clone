import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.message import Message
from schemas.message import MessageCreate, MessageUpdate
from services.message_service import MessageService


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(repo: MagicMock) -> MessageService:
    return MessageService(repo)


@pytest.mark.asyncio
async def test_send_message_creates_and_loads_with_author(
    service: MessageService, repo: MagicMock
):
    author_id = uuid.uuid4()
    channel_id = uuid.uuid4()
    created = Message(
        content="hello",
        author_id=author_id,
        channel_id=channel_id,
    )
    created.id = uuid.uuid4()
    created.created_at = datetime.now(timezone.utc)
    loaded = Message(
        content="hello",
        author_id=author_id,
        channel_id=channel_id,
    )
    loaded.id = created.id
    loaded.created_at = created.created_at
    repo.create = AsyncMock(return_value=created)
    repo.get_by_id_with_author = AsyncMock(return_value=loaded)

    out = await service.send_message(
        author_id, channel_id, MessageCreate(content="hello")
    )

    assert out is loaded
    repo.create.assert_awaited_once()
    repo.get_by_id_with_author.assert_awaited_once_with(created.id)


@pytest.mark.asyncio
async def test_get_channel_messages(service: MessageService, repo: MagicMock):
    cid = uuid.uuid4()
    repo.get_by_channel = AsyncMock(return_value=[])
    assert await service.get_channel_messages(cid, limit=10, offset=2) == []
    repo.get_by_channel.assert_awaited_once_with(cid, limit=10, offset=2)


@pytest.mark.asyncio
async def test_update_message_success(service: MessageService, repo: MagicMock):
    uid = uuid.uuid4()
    msg = Message(content="a", author_id=uid, channel_id=uuid.uuid4())
    msg.id = uuid.uuid4()
    msg.created_at = datetime.now(timezone.utc)
    repo.save = AsyncMock(side_effect=lambda m: m)
    repo.get_by_id_with_author = AsyncMock(side_effect=lambda mid: msg)

    out = await service.update_message(
        msg, MessageUpdate(content="b"), requestor_id=uid
    )

    assert out.content == "b"
    assert msg.updated_at is not None


@pytest.mark.asyncio
async def test_update_message_forbidden_for_non_author(
    service: MessageService, repo: MagicMock
):
    msg = Message(
        content="a",
        author_id=uuid.uuid4(),
        channel_id=uuid.uuid4(),
    )
    with pytest.raises(PermissionError, match="Cannot edit"):
        await service.update_message(
            msg, MessageUpdate(content="b"), requestor_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_delete_message_success(service: MessageService, repo: MagicMock):
    uid = uuid.uuid4()
    msg = Message(content="x", author_id=uid, channel_id=uuid.uuid4())
    repo.delete = AsyncMock(return_value=None)
    await service.delete_message(msg, requestor_id=uid)
    repo.delete.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_delete_message_forbidden(service: MessageService, repo: MagicMock):
    msg = Message(
        content="x",
        author_id=uuid.uuid4(),
        channel_id=uuid.uuid4(),
    )
    with pytest.raises(PermissionError, match="Cannot delete"):
        await service.delete_message(msg, requestor_id=uuid.uuid4())
