# Uruchom z katalogu backend: .\scripts\init_db.ps1
# Opcjonalnie nadpisze DATABASE_URL, jeśli nie masz .env.
$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql+asyncpg://postgres:admin@127.0.0.1:9232/postgres"
}

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" -m scripts.init_db
} else {
    uv run python -m scripts.init_db
}
