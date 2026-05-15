"""Create initial users/roles indexes and seed default roles."""

from datetime import datetime, timezone

migration_id = "005_create_users_and_roles"
description = "Create user and role indexes and seed default system roles"
created_at = "2026-04-25T18:00:00"
author = "codex@openai.com"


DEFAULT_ROLES = [
    {
        "name": "user",
        "description": "Default role for authenticated users",
        "permissions": ["documents:read", "profile:read"],
    },
    {
        "name": "admin",
        "description": "Administrative role with elevated permissions",
        "permissions": ["documents:read", "documents:write", "users:manage"],
    },
]


async def up(db):
    """Create user/role indexes and ensure default roles exist."""
    current_time = datetime.now(timezone.utc)

    await db.users.update_many(
        {"role_ids": {"$exists": False}},
        {"$set": {"role_ids": [], "updated_at": current_time}},
    )

    await db.users.create_index(
        "email", background=True, name="idx_users_email_unique", unique=True
    )
    await db.users.create_index(
        "username", background=True, name="idx_users_username_unique", unique=True
    )
    await db.users.create_index(
        [("created_at", -1)], background=True, name="idx_users_created_at_desc"
    )

    await db.roles.create_index(
        "name", background=True, name="idx_roles_name_unique", unique=True
    )
    await db.roles.create_index(
        [("created_at", -1)], background=True, name="idx_roles_created_at_desc"
    )

    for role in DEFAULT_ROLES:
        await db.roles.update_one(
            {"name": role["name"]},
            {
                "$setOnInsert": {
                    **role,
                    "is_active": True,
                    "is_system": True,
                    "created_at": current_time,
                    "updated_at": current_time,
                }
            },
            upsert=True,
        )


async def down(db):
    """Drop user/role indexes and remove seeded system roles."""
    await db.users.drop_index("idx_users_email_unique")
    await db.users.drop_index("idx_users_username_unique")
    await db.users.drop_index("idx_users_created_at_desc")

    await db.roles.drop_index("idx_roles_name_unique")
    await db.roles.drop_index("idx_roles_created_at_desc")

    await db.users.update_many({}, {"$unset": {"role_ids": ""}})
    await db.roles.delete_many({"is_system": True, "name": {"$in": ["user", "admin"]}})
