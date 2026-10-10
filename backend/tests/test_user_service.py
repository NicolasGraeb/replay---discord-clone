import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from models.user import User
from schemas.user import UserCreate, UserUpdate
from services.user_service import UserService


@pytest.fixture
def user_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(user_repo: MagicMock) -> UserService:
    return UserService(user_repo)


@pytest.mark.asyncio
async def test_register_creates_user_when_email_and_username_free(
    service: UserService, user_repo: MagicMock
):
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_username = AsyncMock(return_value=None)
    saved = User(
        username="newbie",
        email="newbie@example.com",
        hashed_password="hashed",
    )
    saved.id = uuid.uuid4()
    user_repo.create = AsyncMock(return_value=saved)

    data = UserCreate(username="newbie", email="newbie@example.com", password="password-12")
    out = await service.register(data)

    assert out is saved
    user_repo.create.assert_awaited_once()
    created_arg = user_repo.create.await_args.args[0]
    assert created_arg.username == "newbie"
    assert created_arg.email == "newbie@example.com"
    assert created_arg.hashed_password != "password-12"


@pytest.mark.asyncio
async def test_register_raises_when_email_in_use(service: UserService, user_repo: MagicMock):
    user_repo.get_by_email = AsyncMock(return_value=MagicMock())

    with pytest.raises(ValueError, match="Email already in use"):
        await service.register(
            UserCreate(
                username="usr",
                email="taken@example.com",
                password="password-12",
            )
        )


@pytest.mark.asyncio
async def test_register_raises_when_username_taken(
    service: UserService, user_repo: MagicMock
):
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_username = AsyncMock(return_value=MagicMock())

    with pytest.raises(ValueError, match="Username already taken"):
        await service.register(
            UserCreate(username="taken", email="free@example.com", password="password-12")
        )


@pytest.mark.asyncio
async def test_update_username_success(service: UserService, user_repo: MagicMock, sample_user: User):
    user_repo.get_by_username = AsyncMock(return_value=None)
    user_repo.save = AsyncMock(side_effect=lambda u: u)

    out = await service.update(sample_user, UserUpdate(username="renamed"))

    assert out.username == "renamed"
    user_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_avatar_url_can_clear_with_null(
    service: UserService, user_repo: MagicMock, sample_user: User
):
    sample_user.avatar_url = "https://example.com/a.png"
    user_repo.save = AsyncMock(side_effect=lambda u: u)

    out = await service.update(sample_user, UserUpdate(avatar_url=None))

    assert out.avatar_url is None
    user_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_username_raises_when_taken_by_other(
    service: UserService, user_repo: MagicMock, sample_user: User, other_user_id: uuid.UUID
):
    other = MagicMock()
    other.id = other_user_id
    user_repo.get_by_username = AsyncMock(return_value=other)

    with pytest.raises(ValueError, match="Username already taken"):
        await service.update(sample_user, UserUpdate(username="someone"))


@pytest.mark.asyncio
async def test_delete_delegates_to_repository(
    service: UserService, user_repo: MagicMock, sample_user: User
):
    user_repo.delete = AsyncMock(return_value=None)
    await service.delete(sample_user)
    user_repo.delete.assert_awaited_once_with(sample_user)


def test_user_create_schema_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(username="abc", email="a@b.co", password="short")


def test_user_create_schema_accepts_valid_payload():
    u = UserCreate(username="validname", email="v@example.com", password="longenough")
    assert u.username == "validname"
