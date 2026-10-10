from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# MinIO (S3) — obrazki w czacie. Domyślnie jak `docker-compose` (127.0.0.1:9000).
# MINIO_DISABLED=1 — całkowicie wyłącza upload (503 na /messages/image).
MINIO_DISABLED = (os.getenv("MINIO_DISABLED") or "").lower() in ("1", "true", "yes")
_raw_minio_endpoint = (os.getenv("MINIO_ENDPOINT") or "").strip().rstrip("/")
MINIO_ENDPOINT = (
    ""
    if MINIO_DISABLED
    else (_raw_minio_endpoint or "http://127.0.0.1:9000")
)
MINIO_ACCESS_KEY = (os.getenv("MINIO_ACCESS_KEY") or "minioadmin").strip()
MINIO_SECRET_KEY = (os.getenv("MINIO_SECRET_KEY") or "minioadmin").strip()
MINIO_BUCKET = (os.getenv("MINIO_BUCKET") or "relay-images").strip()
MINIO_PUBLIC_URL = (
    (os.getenv("MINIO_PUBLIC_URL") or "").strip().rstrip("/")
    or MINIO_ENDPOINT
    or "http://127.0.0.1:9000"
)
IMAGE_MAX_EDGE = int(os.getenv("IMAGE_MAX_EDGE", "1920"))
CHAT_IMAGE_MAX_UPLOAD_BYTES = int(os.getenv("CHAT_IMAGE_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
AVATAR_MAX_UPLOAD_BYTES = int(os.getenv("AVATAR_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
# Presigned GET dla <img src> (brak Bearer); sekundy ważności linku
CHAT_IMAGE_URL_EXPIRE_SECONDS = int(
    os.getenv("CHAT_IMAGE_URL_EXPIRE_SECONDS", str(7 * 24 * 3600))
)
