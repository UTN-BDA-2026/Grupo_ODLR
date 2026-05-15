import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

os.environ["DEBUG"] = "true"

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, hash_password
from app.services.auth_service import AuthService


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db["users"] = MagicMock()
    return db


def build_user_document(user_id: ObjectId | None = None, **overrides):
    now = datetime.now(timezone.utc)
    document = {
        "_id": user_id or ObjectId(),
        "email": "user@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "hashed_password": hash_password("plain-password"),
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }
    document.update(overrides)
    return document


@pytest.mark.asyncio
async def test_login_returns_bearer_token(auth_service, mock_db):
    mock_db["users"].find_one = AsyncMock(return_value=build_user_document())

    result = await auth_service.login(mock_db, "testuser", "plain-password")

    assert result.token_type == "bearer"
    assert isinstance(result.access_token, str)
    assert result.access_token.count(".") == 2


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(auth_service, mock_db):
    mock_db["users"].find_one = AsyncMock(return_value=build_user_document())

    with pytest.raises(
        UnauthorizedException, match="Incorrect username/email or password"
    ):
        await auth_service.login(mock_db, "testuser", "wrong-password")


@pytest.mark.asyncio
async def test_get_current_user_returns_user_from_token(auth_service, mock_db):
    user_id = ObjectId()
    mock_db["users"].find_one = AsyncMock(return_value=build_user_document(user_id))
    token = create_access_token(str(user_id))

    result = await auth_service.get_current_user(mock_db, token)

    assert result.id == str(user_id)
    assert result.email == "user@example.com"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(auth_service, mock_db):
    with pytest.raises(UnauthorizedException, match="Invalid authentication token"):
        await auth_service.get_current_user(mock_db, "invalid-token")
