"""
Add user metadata fields to documents.

Adds user_id and organization_id fields with proper indexing.
"""

from datetime import datetime, timezone

migration_id = "004_add_user_metadata"
description = "Add user_id and organization_id fields to documents"
created_at = "2024-01-15T13:00:00"
author = "developer@company.com"


async def up(db):
    """
    Add user metadata fields and create indexes.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    current_time = datetime.now(timezone.utc)

    # First, add the new fields to existing documents
    result = await db.documents.update_many(
        filter={"user_id": {"$exists": False}},
        update={
            "$set": {
                "user_id": None,
                "organization_id": None,
                "updated_at": current_time,
            }
        },
    )

    print(f"  Added user fields to {result.modified_count} documents")

    # Create indexes for the new fields
    await db.documents.create_index(
        "user_id",
        background=True,
        name="idx_user_id",
        sparse=True,  # Only index documents with user_id
    )

    await db.documents.create_index(
        "organization_id", background=True, name="idx_organization_id", sparse=True
    )

    # Compound index for user's documents
    await db.documents.create_index(
        [("user_id", 1), ("created_at", -1)], background=True, name="idx_user_created"
    )

    print("  Created indexes for user fields")


async def down(db):
    """
    Remove user metadata fields and drop indexes.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    # Drop indexes first
    await db.documents.drop_index("idx_user_id")
    await db.documents.drop_index("idx_organization_id")
    await db.documents.drop_index("idx_user_created")

    print("  Dropped user field indexes")

    # Remove the fields
    result = await db.documents.update_many(
        filter={}, update={"$unset": {"user_id": "", "organization_id": ""}}
    )

    print(f"  Removed user fields from {result.modified_count} documents")
