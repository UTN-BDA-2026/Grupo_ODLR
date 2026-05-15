"""
Transform metadata field from string to object format.

Migrates legacy string metadata to structured object format.
"""

from datetime import datetime, timezone

migration_id = "003_transform_document_fields"
description = "Transform metadata from string to object format"
created_at = "2024-01-15T12:00:00"
author = "developer@company.com"


async def up(db):
    """
    Transform string metadata to object format.

    Converts documents where metadata is a string to an object
    with 'source' and 'version' fields.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    current_time = datetime.now(timezone.utc)
    migrated_count = 0
    error_count = 0

    # Find documents with string metadata
    cursor = db.documents.find({"metadata": {"$type": "string"}})

    async for doc in cursor:
        try:
            old_metadata = doc.get("metadata", "")

            # Transform to object format
            new_metadata = {
                "source": old_metadata,
                "version": 1,
                "migrated_at": current_time.isoformat(),
            }

            await db.documents.update_one(
                {"_id": doc["_id"]},
                {"$set": {"metadata": new_metadata, "updated_at": current_time}},
            )
            migrated_count += 1

        except Exception as e:
            print(f"  Error migrating document {doc['_id']}: {e}")
            error_count += 1

    print(f"  Migrated {migrated_count} documents, {error_count} errors")


async def down(db):
    """
    Revert object metadata back to string format.

    Extracts the 'source' field and sets it as the metadata value.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    current_time = datetime.now(timezone.utc)
    reverted_count = 0
    error_count = 0

    # Find documents with object metadata that has our specific format
    cursor = db.documents.find(
        {"metadata": {"$type": "object"}, "metadata.source": {"$exists": True}}
    )

    async for doc in cursor:
        try:
            metadata = doc.get("metadata", {})

            # Revert to string format
            if isinstance(metadata, dict) and "source" in metadata:
                old_value = metadata["source"]

                await db.documents.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"metadata": old_value, "updated_at": current_time}},
                )
                reverted_count += 1

        except Exception as e:
            print(f"  Error reverting document {doc['_id']}: {e}")
            error_count += 1

    print(f"  Reverted {reverted_count} documents, {error_count} errors")
