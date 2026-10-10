import uuid
from datetime import datetime, timedelta, timezone

from config.envs import REFRESH_TOKEN_EXPIRE_DAYS
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from models.refresh_token import RefreshToken
from models.user import User
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.user_repository import UserRepository


def _utc_naive_for_db(dt: datetime) -> datetime:
    """TIMESTAMP WITHOUT TIME ZONE: persist UTC as naive (asyncpg / PG)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _as_utc_aware(dt: datetime) -> datetime:
    """Normalize DB datetime (naive UTC or aware) for comparison with aware now."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    async def issue_tokens(self, user: User) -> tuple[str, str]:
        """Returns (access_token, refresh_token). Saves refresh JTI to DB."""
        access_token = create_access_token(user.id)
        refresh_token_str, jti = create_refresh_token(user.id)

        record = RefreshToken(
            id=jti,
            user_id=user.id,
            expires_at=_utc_naive_for_db(
                datetime.now(timezone.utc)
                + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            ),
        )
        await self.token_repo.create(record)
        return access_token, refresh_token_str

    async def rotate_tokens(self, raw_refresh_token: str) -> tuple[str, str]:
        """Validates refresh token, revokes it, issues a fresh pair (rotation)."""
        try:
            user_id, jti = decode_refresh_token(raw_refresh_token)
        except ValueError:
            raise PermissionError("Invalid refresh token")

        record = await self.token_repo.get_by_jti(jti)
        if not record or record.revoked:
            # Possible token reuse — revoke ALL tokens for the user (breach signal)
            if record:
                await self.token_repo.revoke_all_for_user(record.user_id)
            raise PermissionError("Refresh token already used or not found")

        now = datetime.now(timezone.utc)
        if _as_utc_aware(record.expires_at) < now:
            raise PermissionError("Refresh token expired")

        record.revoked = True
        await self.token_repo.save(record)

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise PermissionError("User not found")

        return await self.issue_tokens(user)

    async def revoke_token(self, raw_refresh_token: str) -> None:
        try:
            _, jti = decode_refresh_token(raw_refresh_token)
        except ValueError:
            return
        record = await self.token_repo.get_by_jti(jti)
        if record and not record.revoked:
            record.revoked = True
            await self.token_repo.save(record)
