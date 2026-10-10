import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from config.envs import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    """Returns (encoded_token, jti) — jti is stored in DB for revocation."""
    jti = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "jti": str(jti),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM), jti


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Invalid or expired access token")
    if payload.get("type") != "access":
        raise ValueError("Wrong token type")
    return uuid.UUID(payload["sub"])


def decode_refresh_token(token: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Returns (user_id, jti)."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise ValueError("Wrong token type")
    return uuid.UUID(payload["sub"]), uuid.UUID(payload["jti"])
