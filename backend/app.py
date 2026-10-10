from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import get_engine
from controllers.auth_controller import router as auth_router
from controllers.channel_controller import router as channel_router
from controllers.message_controller import router as message_router
from controllers.server_controller import router as server_router
from controllers.user_controller import router as user_router
from core.dependencies import get_current_user
from core.startup_db import run_startup_migrations
from ws.channel_ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_startup_migrations(get_engine())
    yield


app = FastAPI(title="Discord Clone API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Public routes (no auth required) ---
app.include_router(auth_router)   # /auth/login, /auth/refresh, /auth/logout
app.include_router(user_router)   # /users/register is public; /users/me etc. enforce auth individually

# --- Protected routes (valid JWT required for every endpoint) ---
_auth = [Depends(get_current_user)]
app.include_router(server_router,  dependencies=_auth)
app.include_router(channel_router, dependencies=_auth)
app.include_router(message_router, dependencies=_auth)

# WebSocket: auth handled per-connection via ?token= query param
app.include_router(ws_router)
