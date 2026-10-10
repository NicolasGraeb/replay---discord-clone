import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from core.security import decode_access_token
from models.server_member import MemberRole, ServerMember
from models.user import User
from repositories.server_member_repository import ServerMemberRepository
from repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_ROLE_HIERARCHY: dict[MemberRole, int] = {
    MemberRole.MEMBER: 0,
    MemberRole.MODERATOR: 1,
    MemberRole.ADMIN: 2,
    MemberRole.OWNER: 3,
}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise exc
    user = await UserRepository(session).get_by_id(user_id)
    if not user:
        raise exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_server_role(minimum_role: MemberRole):
    """
    Dependency factory for server-scoped RBAC.

    Usage:
        member: ServerMember = Depends(require_server_role(MemberRole.ADMIN))

    FastAPI resolves `server_id` from the path parameter automatically.
    Returns the caller's ServerMember so endpoints can inspect it if needed.
    """
    async def _check(
        server_id: uuid.UUID,
        current_user: CurrentUser,
        session: AsyncSession = Depends(get_session),
    ) -> ServerMember:
        member = await ServerMemberRepository(session).get(current_user.id, server_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this server",
            )
        if _ROLE_HIERARCHY[member.role] < _ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return member

    return _check


# Convenience aliases — use these in controller signatures
AnyServerMember = Annotated[ServerMember, Depends(require_server_role(MemberRole.MEMBER))]
ServerModerator = Annotated[ServerMember, Depends(require_server_role(MemberRole.MODERATOR))]
ServerAdmin = Annotated[ServerMember, Depends(require_server_role(MemberRole.ADMIN))]
ServerOwner = Annotated[ServerMember, Depends(require_server_role(MemberRole.OWNER))]
