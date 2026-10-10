from controllers.auth_controller import router as auth_router
from controllers.channel_controller import router as channel_router
from controllers.message_controller import router as message_router
from controllers.server_controller import router as server_router
from controllers.user_controller import router as user_router

__all__ = [
    "auth_router",
    "user_router",
    "server_router",
    "channel_router",
    "message_router",
]
