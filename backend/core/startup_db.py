"""Lekkie migracje DDL przy starcie API (idempotentne)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# PostgreSQL: brak tabeli messages = tylko notice; stara baza bez kolumny = dodanie
_STARTUP_DDL = (
    "ALTER TABLE IF EXISTS messages ADD COLUMN IF NOT EXISTS image_key VARCHAR(512);",
)


async def run_startup_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for stmt in _STARTUP_DDL:
            await conn.execute(text(stmt))
