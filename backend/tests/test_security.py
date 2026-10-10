import uuid

import pytest
from jose import jwt

from config.envs import JWT_ALGORITHM, JWT_SECRET_KEY
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify_roundtrip():
    h = hash_password("my-secret-password-12")
    assert h != "my-secret-password-12"
    assert verify_password("my-secret-password-12", h) is True


def test_verify_password_rejects_wrong_plain():
    h = hash_password("only-one-password-12")
    assert verify_password("other-password-12", h) is False


def test_create_access_token_decode_roundtrip(user_id: uuid.UUID):
    token = create_access_token(user_id)
    assert isinstance(token, str)
    assert decode_access_token(token) == user_id


def test_decode_access_token_rejects_refresh_token(user_id: uuid.UUID):
    refresh_str, _jti = create_refresh_token(user_id)
    with pytest.raises(ValueError, match="Wrong token type"):
        decode_access_token(refresh_str)


def test_decode_access_token_rejects_garbage():
    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token("not.a.jwt")


def test_create_refresh_token_decode_roundtrip(user_id: uuid.UUID):
    token, jti = create_refresh_token(user_id)
    uid, out_jti = decode_refresh_token(token)
    assert uid == user_id
    assert out_jti == jti


def test_decode_refresh_token_rejects_access_token(user_id: uuid.UUID):
    access = create_access_token(user_id)
    with pytest.raises(ValueError, match="Wrong token type"):
        decode_refresh_token(access)


def test_jwt_payload_contains_expected_claims(user_id: uuid.UUID):
    access = create_access_token(user_id)
    payload = jwt.decode(access, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload

    refresh, jti = create_refresh_token(user_id)
    rp = jwt.decode(refresh, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert rp["sub"] == str(user_id)
    assert rp["type"] == "refresh"
    assert rp["jti"] == str(jti)
