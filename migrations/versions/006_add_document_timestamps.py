"""
Add created_at and updated_at to existing documents.

Backfills timestamps for documents that were created before
the DocumentService began persisting these fields.
"""

from datetime import datetime, timezone

migration_id = "006_add_document_timestamps"
description = "Add created_at and updated_at to existing documents"
created_at = "2026-04-29T00:00:00"
author = "santinoolivetti810@gmail.com"

_FALLBACK = datetime(2024, 1, 1, tzinfo=timezone.utc)


async def up(db):
    cursor = db.documents.find({"created_at": {"$exists": False}})
    updated = 0
    async for doc in cursor:
        await db.documents.update_one(
            {"_id": doc["_id"]},
            {"$set": {"created_at": _FALLBACK, "updated_at": _FALLBACK}},
        )
        updated += 1
    print(f"  Backfilled timestamps on {updated} documents")


async def down(db):
    result = await db.documents.update_many(
        {"created_at": _FALLBACK},
        {"$unset": {"created_at": "", "updated_at": ""}},
    )
    print(f"  Removed timestamps from {result.modified_count} documents")
