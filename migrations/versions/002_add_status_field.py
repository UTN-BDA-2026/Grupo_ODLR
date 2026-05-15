"""
Add status field to existing documents.

Backfills documents with a default status value.
"""

from datetime import datetime, timezone

migration_id = "002_add_status_field"
description = "Add status field to existing documents with default value"
created_at = "2024-01-15T11:00:00"
author = "developer@company.com"


async def up(db):
    """
    Add status field to documents that don't have it.

    Sets status to 'pending' for all documents without a status.
    Also sets the updated_at timestamp.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    current_time = datetime.now(timezone.utc)

    result = await db.documents.update_many(
        filter={"status": {"$exists": False}},
        update={"$set": {"status": "pending", "updated_at": current_time}},
    )

    # Log the result (this will be printed if using the migration runner)
    print(f"  Updated {result.modified_count} documents with status='pending'")


async def down(db):
    """
    Remove status field from all documents.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    result = await db.documents.update_many(
        filter={}, update={"$unset": {"status": ""}}
    )

    print(f"  Removed status field from {result.modified_count} documents")
