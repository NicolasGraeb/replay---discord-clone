"""Synchroniczny zapis do MinIO (S3-compatible) przez boto3."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import boto3

logger = logging.getLogger(__name__)
from botocore.client import Config

from config.envs import (
    CHAT_IMAGE_URL_EXPIRE_SECONDS,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_DISABLED,
    MINIO_ENDPOINT,
    MINIO_PUBLIC_URL,
    MINIO_SECRET_KEY,
)


def media_upload_configured() -> bool:
    if MINIO_DISABLED:
        return False
    return bool(MINIO_ENDPOINT and MINIO_BUCKET)


@lru_cache
def _s3_client():
    return _client_for_endpoint(MINIO_ENDPOINT)


@lru_cache
def _public_s3_client():
    # Sign with the browser-visible host; changing it after signing breaks S3 auth.
    return _client_for_endpoint(MINIO_PUBLIC_URL)


def _client_for_endpoint(endpoint: str):
    if not media_upload_configured():
        raise RuntimeError("MinIO nie jest skonfigurowane (MINIO_ENDPOINT / MINIO_BUCKET)")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def put_chat_object(key: str, body: bytes, content_type: str) -> None:
    client = _s3_client()
    client.put_object(
        Bucket=MINIO_BUCKET,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def delete_object_key(key: str) -> None:
    if not key or not media_upload_configured():
        return
    try:
        client = _s3_client()
        client.delete_object(Bucket=MINIO_BUCKET, Key=key)
    except Exception as e:
        logger.warning("MinIO delete failed for key %s: %s", key, e)


def public_url_for_key(key: Optional[str]) -> Optional[str]:
    """Bez podpisu — działa tylko przy publicznym odczycie bucketa (np. dev)."""
    if not key:
        return None
    base = MINIO_PUBLIC_URL.rstrip("/")
    b = MINIO_BUCKET.strip("/")
    return f"{base}/{b}/{key}"


def signed_image_url(key: Optional[str]) -> Optional[str]:
    """
    Presigned GET — przeglądarka może załadować <img src> bez nagłówka Authorization
    (w przeciwieństwie do surowego URL MinIO z typową polityką prywatną).
    """
    if not key or not media_upload_configured():
        return None
    try:
        client = _public_s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": MINIO_BUCKET, "Key": key},
            ExpiresIn=max(60, min(CHAT_IMAGE_URL_EXPIRE_SECONDS, 604800)),
        )
    except Exception as e:
        logger.warning("MinIO presign failed for key %s: %s", key, e)
        return None
