import uuid
from typing import Optional

from core.security import hash_password, verify_password
from models.user import User
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def register(self, data: UserCreate) -> User:
        if await self.repo.get_by_email(data.email):
            raise ValueError("Email already in use")
        if await self.repo.get_by_username(data.username):
            raise ValueError("Username already taken")
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        return await self.repo.create(user)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return await self.repo.get_by_id(user_id)

    async def update(self, user: User, data: UserUpdate) -> User:
        payload = data.model_dump(exclude_unset=True)
        if "username" in payload:
            uname = payload["username"]
            if uname is not None:
                existing = await self.repo.get_by_username(uname)
                if existing and existing.id != user.id:
                    raise ValueError("Username already taken")
                user.username = uname
        if "avatar_url" in payload:
            raw = payload["avatar_url"]
            if raw is None:
                user.avatar_url = None
            else:
                cleaned = raw.strip()
                user.avatar_url = cleaned or None
        return await self.repo.save(user)

    async def delete(self, user: User) -> None:
        await self.repo.delete(user)

    async def set_avatar_key(self, user: User, key: str) -> User:
        user.avatar_url = key.strip()
        return await self.repo.save(user)

    async def clear_avatar(self, user: User) -> User:
        user.avatar_url = None
        return await self.repo.save(user)
