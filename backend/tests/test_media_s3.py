from urllib.parse import urlparse

from core import media_s3


def test_docker_upload_and_signed_url_use_different_endpoints(monkeypatch):
    monkeypatch.setattr(media_s3, "MINIO_DISABLED", False)
    monkeypatch.setattr(media_s3, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(media_s3, "MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr(media_s3, "MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setattr(media_s3, "MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setattr(media_s3, "MINIO_BUCKET", "relay-images")
    media_s3._s3_client.cache_clear()
    media_s3._public_s3_client.cache_clear()
    try:
        assert media_s3._s3_client().meta.endpoint_url == "http://minio:9000"
        url = media_s3.signed_image_url("messages/example.webp")
        parsed = urlparse(url)
        assert parsed.netloc == "localhost:9000"
        assert parsed.path == "/relay-images/messages/example.webp"
        assert "X-Amz-Signature=" in parsed.query
    finally:
        media_s3._s3_client.cache_clear()
        media_s3._public_s3_client.cache_clear()
