from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from app.models.user import UserCreateDocument
from app.repositories.user_repository import UserRepository


def test_create_user_repository_returns_user_document():
    db = MagicMock()
    db["users"] = MagicMock()
    inserted_id = ObjectId()
    db["users"].insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

    repository = UserRepository(db)
    payload = UserCreateDocument(
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed-password",
        role_ids=[],
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    user = __import__("asyncio").run(repository.create(payload))

    assert user.id == str(inserted_id)
    assert user.email == "user@example.com"
    assert user.hashed_password == "hashed-password"


def test_get_by_identifier_queries_email_or_username():
    db = MagicMock()
    db["users"] = MagicMock()
    db["users"].find_one = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "email": "user@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": "hashed-password",
            "role_ids": [],
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    repository = UserRepository(db)
    user = __import__("asyncio").run(repository.get_by_identifier("testuser"))

    assert user is not None
    query = db["users"].find_one.call_args[0][0]
    assert query == {"$or": [{"email": "testuser"}, {"username": "testuser"}]}
