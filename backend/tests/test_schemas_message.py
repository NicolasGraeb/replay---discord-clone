import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.message import Message
from models.user import User
from schemas.message import MessageCreate, MessageResponse, message_to_response


def test_message_create_validation():
    with pytest.raises(ValidationError):
        MessageCreate(content="")
    m = MessageCreate(content="ok")
    assert m.content == "ok"


def test_message_to_response_with_author():
    uid = uuid.uuid4()
    aid = uuid.uuid4()
    cid = uuid.uuid4()
    author = User(username="bob", email="bob@example.com", hashed_password="x")
    author.id = aid
    msg = Message(content="hi", author_id=aid, channel_id=cid)
    msg.id = uid
    msg.created_at = datetime.now(timezone.utc)
    msg.updated_at = None
    msg.author = author

    dto = message_to_response(msg)

    assert isinstance(dto, MessageResponse)
    assert dto.author_username == "bob"
    assert dto.author_avatar_url is None
    assert dto.content == "hi"
    assert dto.image_url is None


def test_message_to_response_without_author():
    uid = uuid.uuid4()
    aid = uuid.uuid4()
    cid = uuid.uuid4()
    msg = Message(content="x", author_id=aid, channel_id=cid)
    msg.id = uid
    msg.created_at = datetime.now(timezone.utc)
    msg.updated_at = None

    dto = message_to_response(msg)

    assert dto.author_username == "?"
    assert dto.author_avatar_url is None
    assert dto.image_url is None
