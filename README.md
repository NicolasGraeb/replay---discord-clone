![Relay app screenshot](./sc.png)

# Discord Clone (RELAY)

A full-stack chat application inspired by Discord: servers, text and voice channels, real-time messaging, image uploads, user profiles with avatars, and peer-to-peer voice on voice channels (WebRTC).

---

## Tech stack

| Layer | Technologies |
|--------|----------------|
| **Frontend** | [Next.js](https://nextjs.org/) 16 (App Router), React 19, TypeScript, Tailwind CSS 4, [TanStack Query](https://tanstack.com/query), WebSocket + WebRTC |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/), Python 3.11+, SQLAlchemy 2 (async), Pydantic |
| **Database** | PostgreSQL 16 |
| **Object storage** | MinIO (S3-compatible) - chat images and avatars |
| **Auth** | JWT access tokens + refresh tokens (rotation, DB-backed `jti`), bcrypt passwords |
| **Real-time** | WebSockets - text chat live updates; voice channels use the same socket for signaling and chat |
| **Tooling** | `uv` (Python), npm, Docker Compose (full stack) |

For backend internals (models, auth flow, WebSocket details), see **[backend/README.md](./backend/README.md)**.

---

## Features

- Register / login / logout with token refresh
- Create and join servers (invite by server UUID)
- Text channels - messages, replies UI, image attachments (compressed WebP in MinIO)
- Voice channels - text chat in the main panel + WebRTC voice (mesh P2P, STUN)
- User profile - avatar upload with circular crop, username update
- Role-based channel management (owner / admin / moderator / member)

---

## Prerequisites

- **Docker** and Docker Compose
- For development outside Docker: **Node.js** 20.9+ and npm, **Python** 3.11+ and [uv](https://docs.astral.sh/uv/)
- A microphone and browser permission for voice channels

---

## Quick start

### Start everything with Docker Compose

From the project root:

```bash
docker compose up --build -d
```

This starts:

| Service | Ports | Purpose |
|---------|--------|---------|
| Frontend | `3000` | App at http://localhost:3000 |
| Backend | `8000` | API docs at http://localhost:8000/docs |
| PostgreSQL | `9232` → 5432 | Main database |
| MinIO API | `9000` | S3 API |
| MinIO Console | `9001` | Web UI (`minioadmin` / `minioadmin`) |

The `minio-init` job creates the `relay-images` bucket. The backend waits for PostgreSQL and bucket initialization, creates any missing database tables, and starts the API. The frontend starts after the API is healthy.

No local Node.js/Python installation or copied `.env` files are required. Docker uses the environment defined in `docker-compose.yml`; it does not read `backend/.env` or `frontend/app/.env.local`.

Optional overrides can be set in a `.env` file in the project root or in your shell: `JWT_SECRET_KEY`, `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), `MINIO_PUBLIC_URL` (default `http://localhost:9000`), and `NEXT_PUBLIC_RTC_ICE_SERVERS`. For access from another computer, use browser-accessible server addresses instead of `localhost`. Frontend variables are embedded during the build, so rebuild after changing them.

```bash
docker compose logs -f backend frontend
docker compose down
```

`docker compose down` preserves database and uploaded-image volumes. After code changes, run `docker compose up --build -d` again.

### Optional: run backend and frontend locally

Start only the infrastructure (stop Docker's backend/frontend first if already running):

```bash
docker compose stop frontend backend
docker compose up -d postgres minio minio-init
```

#### Backend

```bash
cd backend
cp .env.example .env
# Edit JWT_SECRET_KEY in production

uv sync
uv run python -m scripts.init_db
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

API base URL: **http://127.0.0.1:8000**  
Interactive docs: **http://127.0.0.1:8000/docs**

On Windows you can also run `.\scripts\init_db.ps1` from the `backend` folder.

#### Frontend

```bash
cd frontend/app
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

`NEXT_PUBLIC_API_URL` must point at the backend (default `http://127.0.0.1:8000`).

### Optional - WebRTC behind strict NAT

Set on the frontend (e.g. in `.env.local`):

```env
NEXT_PUBLIC_RTC_ICE_SERVERS=[{"urls":"stun:stun.l.google.com:19302"}]
```

For production or difficult NAT, add a TURN server to that JSON array.

---

## Project structure

```
discord_clone/
├── sc.png                 # App screenshot (hero image in this README)
├── docker-compose.yml     # Frontend + backend + Postgres + MinIO
├── backend/               # FastAPI API + WebSocket
│   ├── app.py
│   ├── models/
│   ├── controllers/
│   ├── services/
│   ├── ws/
│   └── README.md          # Detailed backend documentation
└── frontend/
    └── app/               # Next.js client
        ├── app/           # Routes (/, /login, /register, /profile)
        └── components/relay/
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:admin@127.0.0.1:9232/postgres` |
| `JWT_SECRET_KEY` | Secret for signing JWTs |
| `MINIO_*` | Endpoint, credentials, bucket (`relay-images`) |
| `MINIO_DISABLED=1` | Disables media uploads (503 on image endpoints) |

See `backend/.env.example` for the full list.

### Frontend (`frontend/app/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend origin, e.g. `http://127.0.0.1:8000` |
| `NEXT_PUBLIC_RTC_ICE_SERVERS` | Optional JSON array of ICE servers |

---

## Development

```bash
# Backend tests
cd backend && uv run pytest

# Frontend production build
cd frontend/app && npm run build
```

---

## License

Private / educational project - adjust as needed for your use case.
