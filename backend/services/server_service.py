import uuid
from typing import List, Optional

from models.channel import Channel, ChannelType
from models.server import Server
from models.server_member import MemberRole, ServerMember
from models.user import User
from repositories.channel_repository import ChannelRepository
from repositories.server_member_repository import ServerMemberRepository
from repositories.server_repository import ServerRepository
from repositories.user_repository import UserRepository
from schemas.server import ServerCreate, ServerMemberResponse, ServerUpdate


class ServerService:
    def __init__(
        self,
        server_repo: ServerRepository,
        member_repo: ServerMemberRepository,
        user_repo: UserRepository,
        channel_repo: ChannelRepository,
    ) -> None:
        self.server_repo = server_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.channel_repo = channel_repo

    async def create_server(self, owner: User, data: ServerCreate) -> Server:
        server = Server(name=data.name, owner_id=owner.id, icon_url=data.icon_url)
        server = await self.server_repo.create(server)

        owner_membership = ServerMember(
            user_id=owner.id, server_id=server.id, role=MemberRole.OWNER
        )
        await self.member_repo.create(owner_membership)

        main_ch = Channel(
            name="main",
            server_id=server.id,
            type=ChannelType.TEXT,
        )
        await self.channel_repo.create(main_ch)
        return server

    async def get_server(self, server_id: uuid.UUID) -> Optional[Server]:
        return await self.server_repo.get_by_id(server_id)

    async def list_my_servers(self, user: User) -> List[Server]:
        return await self.server_repo.list_for_user(user.id)

    async def update_server(
        self, server: Server, data: ServerUpdate
    ) -> Server:
        if data.name is not None:
            server.name = data.name
        if data.icon_url is not None:
            server.icon_url = data.icon_url
        return await self.server_repo.save(server)

    async def delete_server(self, server: Server) -> None:
        await self.server_repo.delete(server)

    async def join_server(self, user: User, server: Server) -> ServerMember:
        existing = await self.member_repo.get(user.id, server.id)
        if existing:
            raise ValueError("Already a member of this server")

        member = ServerMember(
            user_id=user.id, server_id=server.id, role=MemberRole.MEMBER
        )
        return await self.member_repo.create(member)

    async def leave_server(self, user_id: uuid.UUID, server: Server) -> None:
        member = await self.member_repo.get(user_id, server.id)
        if not member:
            raise ValueError("Not a member of this server")
        if member.role == MemberRole.OWNER:
            raise ValueError("Owner cannot leave the server")
        await self.member_repo.delete(member)

    async def get_members(self, server_id: uuid.UUID) -> List[ServerMember]:
        return await self.member_repo.get_server_members(server_id)

    async def get_member_rows(self, server_id: uuid.UUID) -> List[ServerMemberResponse]:
        members = await self.member_repo.get_server_members(server_id)
        if not members:
            return []
        user_ids = [m.user_id for m in members]
        users = await self.user_repo.get_by_ids(user_ids)
        out: List[ServerMemberResponse] = []
        for m in members:
            u = users.get(m.user_id)
            out.append(
                ServerMemberResponse(
                    user_id=m.user_id,
                    server_id=m.server_id,
                    role=m.role,
                    joined_at=m.joined_at,
                    username=u.username if u else None,
                )
            )
        return out

    async def update_member_role(
        self,
        server_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: MemberRole,
    ) -> ServerMember:
        member = await self.member_repo.get(target_user_id, server_id)
        if not member:
            raise ValueError("User is not a member of this server")
        if member.role == MemberRole.OWNER:
            raise ValueError("Cannot change the role of the server owner")
        member.role = new_role
        return await self.member_repo.save(member)

    async def require_member(
        self, user_id: uuid.UUID, server_id: uuid.UUID
    ) -> ServerMember:
        member = await self.member_repo.get(user_id, server_id)
        if not member:
            raise PermissionError("Not a member of this server")
        return member
