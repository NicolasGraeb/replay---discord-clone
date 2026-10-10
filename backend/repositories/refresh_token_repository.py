import uuid
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshToken
from repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RefreshToken, session)

    async def get_by_jti(self, jti: uuid.UUID) -> Optional[RefreshToken]:
        return await self.get_by_id(jti)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.session.commit()
