"""
Create initial indexes for documents collection.

Optimizes queries by filename and creation date.
"""

migration_id = "001_create_indexes"
description = "Create initial indexes for documents collection"
created_at = "2024-01-15T10:00:00"
author = "developer@company.com"


async def up(db):
    """
    Create indexes for common query patterns.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    # Index for filename lookups
    await db.documents.create_index("filename", background=True, name="idx_filename")

    # Index for sorting by creation date (descending)
    await db.documents.create_index(
        [("created_at", -1)], background=True, name="idx_created_at_desc"
    )

    # Compound index for filtered queries
    await db.documents.create_index(
        [("status", 1), ("created_at", -1)],
        background=True,
        name="idx_status_created_at",
    )


async def down(db):
    """
    Drop the created indexes.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    await db.documents.drop_index("idx_filename")
    await db.documents.drop_index("idx_created_at_desc")
    await db.documents.drop_index("idx_status_created_at")
