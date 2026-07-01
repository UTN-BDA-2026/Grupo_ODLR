"""
Eliminar índices muertos en la colección audit_log.

Motivo:
La migración 008 creó tres índices, pero la única lectura de audit_log es
get_recent() (app/repositories/audit_repository.py), que hace
find({}).sort("timestamp", -1).limit(...). Ese caso lo cubre
idx_audit_timestamp_desc, que se conserva.

- idx_audit_document_id -> ninguna query filtra audit_log por document_id.
- idx_audit_action      -> ninguna query filtra audit_log por action.
"""

migration_id = "014_drop_dead_audit_indexes"
description = "Drop unused indexes on audit_log collection"
created_at = "2026-06-30T00:03:00"
author = "grupo-pdf-extract-api"


# (nombre, key) para poder restaurar en down()
DEAD_INDEXES = [
    ("idx_audit_document_id", [("document_id", 1)]),
    ("idx_audit_action", [("action", 1)]),
]


async def index_name_exists(collection, index_name: str) -> bool:
    indexes = await collection.index_information()
    return index_name in indexes


async def up(db):
    audit_log = db["audit_log"]

    for name, _key in DEAD_INDEXES:
        if await index_name_exists(audit_log, name):
            await audit_log.drop_index(name)


async def down(db):
    audit_log = db["audit_log"]

    for name, key in DEAD_INDEXES:
        if not await index_name_exists(audit_log, name):
            await audit_log.create_index(key, name=name)
