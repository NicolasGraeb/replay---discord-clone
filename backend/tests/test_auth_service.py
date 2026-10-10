import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.security import create_refresh_token, hash_password
from models.refresh_token import RefreshToken
from models.user import User
from services.auth_service import AuthService


@pytest.fixture
def user_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def token_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_service(user_repo: MagicMock, token_repo: MagicMock) -> AuthService:
    return AuthService(user_repo, token_repo)


@pytest.mark.asyncio
async def test_authenticate_returns_none_when_user_missing(
    auth_service: AuthService, user_repo: MagicMock
):
    user_repo.get_by_email = AsyncMock(return_value=None)
    assert await auth_service.authenticate("x@y.z", "pw") is None


@pytest.mark.asyncio
async def test_authenticate_returns_none_on_bad_password(
    auth_service: AuthService, user_repo: MagicMock, sample_user: User
):
    user_repo.get_by_email = AsyncMock(return_value=sample_user)
    assert await auth_service.authenticate(sample_user.email, "wrong-password") is None


@pytest.mark.asyncio
async def test_authenticate_returns_user_on_success(
    auth_service: AuthService, user_repo: MagicMock, sample_user: User
):
    user_repo.get_by_email = AsyncMock(return_value=sample_user)
    out = await auth_service.authenticate(sample_user.email, "correct-password-12")
    assert out is sample_user


@pytest.mark.asyncio
async def test_issue_tokens_persists_refresh_record(
    auth_service: AuthService, user_repo: MagicMock, token_repo: MagicMock, sample_user: User
):
    token_repo.create = AsyncMock(side_effect=lambda r: r)

    access, refresh = await auth_service.issue_tokens(sample_user)

    assert isinstance(access, str) and isinstance(refresh, str)
    token_repo.create.assert_awaited_once()
    rec = token_repo.create.await_args.args[0]
    assert isinstance(rec, RefreshToken)
    assert rec.user_id == sample_user.id


@pytest.mark.asyncio
async def test_rotate_tokens_raises_on_invalid_jwt(
    auth_service: AuthService, token_repo: MagicMock
):
    with pytest.raises(PermissionError, match="Invalid refresh token"):
        await auth_service.rotate_tokens("not-a-valid-refresh")


@pytest.mark.asyncio
async def test_rotate_tokens_raises_when_record_missing(
    auth_service: AuthService, token_repo: MagicMock, sample_user: User
):
    raw, _jti = create_refresh_token(sample_user.id)
    token_repo.get_by_jti = AsyncMock(return_value=None)

    with pytest.raises(PermissionError, match="not found"):
        await auth_service.rotate_tokens(raw)


@pytest.mark.asyncio
async def test_rotate_tokens_raises_when_revoked(
    auth_service: AuthService, token_repo: MagicMock, user_repo: MagicMock, sample_user: User
):
    raw, jti = create_refresh_token(sample_user.id)
    rec = RefreshToken(
        id=jti,
        user_id=sample_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked=True,
    )
    token_repo.get_by_jti = AsyncMock(return_value=rec)
    token_repo.revoke_all_for_user = AsyncMock(return_value=None)

    with pytest.raises(PermissionError, match="already used"):
        await auth_service.rotate_tokens(raw)


@pytest.mark.asyncio
async def test_rotate_tokens_raises_when_expired(
    auth_service: AuthService, token_repo: MagicMock, user_repo: MagicMock, sample_user: User
):
    raw, jti = create_refresh_token(sample_user.id)
    rec = RefreshToken(
        id=jti,
        user_id=sample_user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        revoked=False,
    )
    token_repo.get_by_jti = AsyncMock(return_value=rec)

    with pytest.raises(PermissionError, match="expired"):
        await auth_service.rotate_tokens(raw)


@pytest.mark.asyncio
async def test_rotate_tokens_success_rotates_and_issues_new_pair(
    auth_service: AuthService, token_repo: MagicMock, user_repo: MagicMock, sample_user: User
):
    raw, jti = create_refresh_token(sample_user.id)
    rec = RefreshToken(
        id=jti,
        user_id=sample_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
    )
    token_repo.get_by_jti = AsyncMock(return_value=rec)
    token_repo.save = AsyncMock(side_effect=lambda r: r)
    user_repo.get_by_id = AsyncMock(return_value=sample_user)
    token_repo.create = AsyncMock(side_effect=lambda r: r)

    access, new_refresh = await auth_service.rotate_tokens(raw)

    assert access and new_refresh
    assert rec.revoked is True
    token_repo.save.assert_awaited()


@pytest.mark.asyncio
async def test_revoke_token_swallows_invalid_jwt(auth_service: AuthService, token_repo: MagicMock):
    token_repo.get_by_jti = AsyncMock()
    await auth_service.revoke_token("!!")
    token_repo.get_by_jti.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_token_marks_record_revoked(
    auth_service: AuthService, token_repo: MagicMock, sample_user: User
):
    raw, jti = create_refresh_token(sample_user.id)
    rec = RefreshToken(
        id=jti,
        user_id=sample_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked=False,
    )
    token_repo.get_by_jti = AsyncMock(return_value=rec)
    token_repo.save = AsyncMock(side_effect=lambda r: r)

    await auth_service.revoke_token(raw)

    assert rec.revoked is True
    token_repo.save.assert_awaited()
