FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.5 /uv /usr/local/bin/uv

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "python -m scripts.init_db && exec uvicorn app:app --host 0.0.0.0 --port 8000"]
