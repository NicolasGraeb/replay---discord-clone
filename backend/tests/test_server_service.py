import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.channel import Channel, ChannelType
from models.server import Server
from models.server_member import MemberRole, ServerMember
from models.user import User
from schemas.server import ServerCreate, ServerUpdate
from services.server_service import ServerService


@pytest.fixture
def server_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def member_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def user_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def channel_repo() -> MagicMock:
    m = MagicMock()
    m.create = AsyncMock(side_effect=lambda c: c)
    return m


@pytest.fixture
def service(
    server_repo: MagicMock,
    member_repo: MagicMock,
    user_repo: MagicMock,
    channel_repo: MagicMock,
) -> ServerService:
    return ServerService(server_repo, member_repo, user_repo, channel_repo)


@pytest.mark.asyncio
async def test_create_server_adds_owner_membership(
    service: ServerService,
    server_repo: MagicMock,
    member_repo: MagicMock,
    channel_repo: MagicMock,
    sample_user: User,
):
    srv = Server(name="Guild", owner_id=sample_user.id, icon_url=None)
    srv.id = uuid.uuid4()
    server_repo.create = AsyncMock(return_value=srv)
    member_repo.create = AsyncMock(side_effect=lambda m: m)

    out = await service.create_server(sample_user, ServerCreate(name="Guild"))

    assert out is srv
    member_arg = member_repo.create.await_args.args[0]
    assert isinstance(member_arg, ServerMember)
    assert member_arg.role == MemberRole.OWNER
    assert member_arg.user_id == sample_user.id
    channel_repo.create.assert_awaited_once()
    ch = channel_repo.create.await_args.args[0]
    assert isinstance(ch, Channel)
    assert ch.name == "main"
    assert ch.type == ChannelType.TEXT
    assert ch.server_id == srv.id


@pytest.mark.asyncio
async def test_join_server_creates_member(
    service: ServerService, member_repo: MagicMock, sample_user: User
):
    srv = Server(name="G", owner_id=uuid.uuid4(), icon_url=None)
    srv.id = uuid.uuid4()
    member_repo.get = AsyncMock(return_value=None)
    member_repo.create = AsyncMock(side_effect=lambda m: m)

    mem = await service.join_server(sample_user, srv)

    assert mem.role == MemberRole.MEMBER
    member_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_join_server_raises_when_already_member(
    service: ServerService, member_repo: MagicMock, sample_user: User
):
    srv = Server(name="G", owner_id=uuid.uuid4(), icon_url=None)
    srv.id = uuid.uuid4()
    member_repo.get = AsyncMock(return_value=MagicMock())

    with pytest.raises(ValueError, match="Already a member"):
        await service.join_server(sample_user, srv)


@pytest.mark.asyncio
async def test_leave_server_owner_forbidden(
    service: ServerService, member_repo: MagicMock, sample_user: User
):
    srv = Server(name="G", owner_id=sample_user.id, icon_url=None)
    srv.id = uuid.uuid4()
    member = ServerMember(
        user_id=sample_user.id,
        server_id=srv.id,
        role=MemberRole.OWNER,
        joined_at=datetime.now(timezone.utc),
    )
    member_repo.get = AsyncMock(return_value=member)

    with pytest.raises(ValueError, match="Owner cannot leave"):
        await service.leave_server(sample_user.id, srv)


@pytest.mark.asyncio
async def test_leave_server_deletes_member(
    service: ServerService, member_repo: MagicMock, sample_user: User
):
    srv = Server(name="G", owner_id=uuid.uuid4(), icon_url=None)
    srv.id = uuid.uuid4()
    member = ServerMember(
        user_id=sample_user.id,
        server_id=srv.id,
        role=MemberRole.MEMBER,
        joined_at=datetime.now(timezone.utc),
    )
    member_repo.get = AsyncMock(return_value=member)
    member_repo.delete = AsyncMock(return_value=None)

    await service.leave_server(sample_user.id, srv)

    member_repo.delete.assert_awaited_once_with(member)


@pytest.mark.asyncio
async def test_leave_server_raises_when_not_member(
    service: ServerService, member_repo: MagicMock, sample_user: User
):
    srv = Server(name="G", owner_id=uuid.uuid4(), icon_url=None)
    srv.id = uuid.uuid4()
    member_repo.get = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Not a member"):
        await service.leave_server(sample_user.id, srv)


@pytest.mark.asyncio
async def test_list_my_servers(service: ServerService, server_repo: MagicMock, sample_user: User):
    server_repo.list_for_user = AsyncMock(return_value=[])
    assert await service.list_my_servers(sample_user) == []
    server_repo.list_for_user.assert_awaited_once_with(sample_user.id)


@pytest.mark.asyncio
async def test_get_member_rows_includes_usernames(
    service: ServerService, member_repo: MagicMock, user_repo: MagicMock, sample_user: User
):
    sid = uuid.uuid4()
    m = ServerMember(
        user_id=sample_user.id,
        server_id=sid,
        role=MemberRole.MEMBER,
        joined_at=datetime.now(timezone.utc),
    )
    m.joined_at = datetime.now(timezone.utc)
    member_repo.get_server_members = AsyncMock(return_value=[m])
    user_repo.get_by_ids = AsyncMock(return_value={sample_user.id: sample_user})

    rows = await service.get_member_rows(sid)

    assert len(rows) == 1
    assert rows[0].username == sample_user.username


@pytest.mark.asyncio
async def test_update_member_role_raises_for_owner(
    service: ServerService, member_repo: MagicMock
):
    sid = uuid.uuid4()
    owner_id = uuid.uuid4()
    member = ServerMember(
        user_id=owner_id,
        server_id=sid,
        role=MemberRole.OWNER,
        joined_at=datetime.now(timezone.utc),
    )
    member_repo.get = AsyncMock(return_value=member)

    with pytest.raises(ValueError, match="Cannot change the role"):
        await service.update_member_role(sid, owner_id, MemberRole.ADMIN)


@pytest.mark.asyncio
async def test_require_member_raises_when_absent(
    service: ServerService, member_repo: MagicMock
):
    member_repo.get = AsyncMock(return_value=None)
    with pytest.raises(PermissionError, match="Not a member"):
        await service.require_member(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_update_server_applies_fields(service: ServerService, server_repo: MagicMock):
    srv = Server(name="Old", owner_id=uuid.uuid4(), icon_url=None)
    srv.id = uuid.uuid4()
    server_repo.save = AsyncMock(side_effect=lambda s: s)

    out = await service.update_server(srv, ServerUpdate(name="New", icon_url="https://x/icon.png"))

    assert out.name == "New"
    assert out.icon_url == "https://x/icon.png"
