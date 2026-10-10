#!/usr/bin/env sh
# Uruchom z katalogu backend: sh scripts/init_db.sh
set -e
cd "$(dirname "$0")/.."
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://postgres:admin@127.0.0.1:9232/postgres}"
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m scripts.init_db
else
  uv run python -m scripts.init_db
fi
