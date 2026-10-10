import uuid

import pytest

from core.security import hash_password
from models.user import User


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def other_user_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def sample_user(user_id: uuid.UUID) -> User:
    u = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hash_password("correct-password-12"),
    )
    u.id = user_id
    return u
