# MongoDB Migration System - Quick Guide

## Overview

This migration system provides a clean, professional way to manage MongoDB schema evolution.

## Philosophy

- **Functions, not classes**: Migrations are pure async functions
- **No SQLAlchemy**: Native MongoDB operations only
- **Track everything**: All migrations are logged in `_migration_log` collection
- **Safe by default**: Dry-run mode, checksums, and locks

## Quick Commands

```bash
# Check status
python -m migrations status

# Run migrations
python -m migrations migrate

# Create new migration
python -m migrations create "add user roles"

# Rollback last
python -m migrations rollback

# Preview changes
python -m migrations migrate --dry-run
```

## Migration File Structure

```python
"""
Brief description of what this migration does.
"""

migration_id = "filename_without_extension"
description = "Human-readable description"
created_at = "2024-01-15T10:00:00"
author = "developer@company.com"


async def up(db):
    """Apply migration."""
    # Your migration code here
    pass


async def down(db):
    """Revert migration."""
    # Your rollback code here
    pass
```

## Common Patterns

### Add Index

```python
async def up(db):
    await db.collection.create_index("field_name", background=True)

async def down(db):
    await db.collection.drop_index("field_name_1")
```

### Add Field with Default

```python
async def up(db):
    await db.collection.update_many(
        {"new_field": {"$exists": False}},
        {"$set": {"new_field": "default_value"}}
    )

async def down(db):
    await db.collection.update_many(
        {},
        {"$unset": {"new_field": ""}}
    )
```

### Transform Documents

```python
async def up(db):
    async for doc in db.collection.find({"old_field": {"$exists": True}}):
        await db.collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"new_field": doc["old_field"]},
             "$unset": {"old_field": ""}}
        )

async def down(db):
    async for doc in db.collection.find({"new_field": {"$exists": True}}):
        await db.collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"old_field": doc["new_field"]},
             "$unset": {"new_field": ""}}
        )
```

## Best Practices

1. **Always write down()**: Makes rollbacks possible
2. **Use background=True**: For index creation to avoid blocking
3. **Test before deploy**: Always use --dry-run first
4. **Keep them small**: One change per migration
5. **Be idempotent**: Migrations can run multiple times safely
6. **Document clearly**: Write good descriptions

## Troubleshooting

### Migration Failed

Check the error and fix the issue, then:

```bash
# If needed, manually fix the _migration_log collection
# Then retry
python -m migrations migrate
```

### Check Applied Migrations

```bash
# Direct MongoDB query
mongo> db._migration_log.find().sort({applied_at: -1})
```

### Reset Migration State (Development Only)

```python
# In Python shell
from motor.motor_asyncio import AsyncIOMotorClient

async def reset():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["pdf_extract_db"]
    await db._migration_log.delete_many({})
    await db._migration_lock.delete_many({})

import asyncio
asyncio.run(reset())
```

## Architecture

```
migrations/
├── runner.py      # Execution engine
├── registry.py    # State tracking
├── cli.py         # CLI interface
└── versions/      # Your migrations
```

The system:
1. Scans `versions/` for migration files
2. Compares with `_migration_log` collection
3. Executes pending migrations in order
4. Logs each migration with checksum
5. Supports rollback via `down()` functions
