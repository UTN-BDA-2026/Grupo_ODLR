from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from app.models.role import RoleCreateDocument
from app.repositories.role_repository import RoleRepository


def test_create_role_repository_returns_role_document():
    db = MagicMock()
    db["roles"] = MagicMock()
    inserted_id = ObjectId()
    db["roles"].insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

    repository = RoleRepository(db)
    payload = RoleCreateDocument(
        name="admin",
        description="Admin role",
        permissions=["users:manage"],
        is_active=True,
        is_system=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    role = __import__("asyncio").run(repository.create(payload))

    assert role.id == str(inserted_id)
    assert role.name == "admin"
    assert role.permissions == ["users:manage"]
