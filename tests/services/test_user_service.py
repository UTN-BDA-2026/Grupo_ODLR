import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

os.environ["DEBUG"] = "true"

from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


@pytest.fixture
def user_service() -> UserService:
    return UserService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db["users"] = MagicMock()
    return db


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_returns_response(user_service, mock_db):
    inserted_id = ObjectId()
    mock_db["users"].find_one = AsyncMock(return_value=None)
    mock_db["users"].insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=inserted_id)
    )

    result = await user_service.create_user(
        mock_db,
        UserCreate(
            email="user@example.com",
            username="testuser",
            full_name="Test User",
            password="plain-password",
        ),
    )

    assert result.id == str(inserted_id)
    assert result.email == "user@example.com"
    inserted_document = mock_db["users"].insert_one.call_args[0][0]
    assert inserted_document["hashed_password"] != "plain-password"
    assert inserted_document["is_active"] is True
    assert inserted_document["is_superuser"] is False


@pytest.mark.asyncio
async def test_create_user_raises_conflict_for_duplicate_email(user_service, mock_db):
    mock_db["users"].find_one = AsyncMock(
        side_effect=[{"_id": ObjectId(), "email": "user@example.com"}]
    )

    with pytest.raises(ConflictException, match="Email already registered"):
        await user_service.create_user(
            mock_db,
            UserCreate(
                email="user@example.com",
                username="testuser",
                full_name="Test User",
                password="plain-password",
            ),
        )


@pytest.mark.asyncio
async def test_get_user_by_id_returns_user(user_service, mock_db):
    user_id = ObjectId()
    mock_db["users"].find_one = AsyncMock(
        return_value={
            "_id": user_id,
            "email": "user@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": "hashed-password",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    result = await user_service.get_user_by_id(mock_db, str(user_id))

    assert result.id == str(user_id)
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_update_user_hashes_new_password(user_service, mock_db):
    user_id = ObjectId()
    now = datetime.now(timezone.utc)
    existing_user = {
        "_id": user_id,
        "email": "user@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "hashed_password": "old-hash",
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }
    updated_user = {
        **existing_user,
        "full_name": "Updated User",
        "hashed_password": "new-hash",
        "updated_at": datetime.now(timezone.utc),
    }
    mock_db["users"].find_one = AsyncMock(side_effect=[existing_user, updated_user])
    mock_db["users"].update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    result = await user_service.update_user(
        mock_db,
        str(user_id),
        UserUpdate(full_name="Updated User", password="new-password"),
    )

    assert result.full_name == "Updated User"
    update_payload = mock_db["users"].update_one.call_args[0][1]["$set"]
    assert update_payload["hashed_password"] != "new-password"
    assert "password" not in update_payload


@pytest.mark.asyncio
async def test_delete_user_raises_not_found_when_missing(user_service, mock_db):
    user_id = ObjectId()
    mock_db["users"].delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))

    with pytest.raises(NotFoundException, match="User not found"):
        await user_service.delete_user(mock_db, str(user_id))
