"""
Tworzy wszystkie tabele w bazie wskazanej przez DATABASE_URL.

Uruchomienie z katalogu backend:
  uv run python -m scripts.init_db
Albo: .\\scripts\\init_db.ps1 (Windows) / ./scripts/init_db.sh (Unix)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models  # noqa: F401 — registers all models with Base.metadata
from config.database import get_engine
from config.envs import DB_URL
from core.startup_db import run_startup_migrations
from models.base import Base


def _require_database_url() -> None:
    if not (DB_URL or "").strip():
        print(
            "Brak DATABASE_URL. Ustaw w pliku backend/.env, np.:\n"
            "  DATABASE_URL=postgresql+asyncpg://postgres:admin@127.0.0.1:9232/postgres\n"
            "(dla async SQLAlchemy musi być prefiks postgresql+asyncpg://)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not DB_URL.startswith("postgresql+asyncpg://"):
        print(
            "DATABASE_URL musi używać sterownika asyncpg, np.:\n"
            "  postgresql+asyncpg://USER:HASLO@HOST:PORT/BAZA",
            file=sys.stderr,
        )
        raise SystemExit(1)


async def init_db() -> None:
    _require_database_url()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await run_startup_migrations(engine)
    await engine.dispose()
    print("Tabele utworzone i migracje DDL zastosowane.")


if __name__ == "__main__":
    asyncio.run(init_db())
