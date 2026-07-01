"""
Create audit log collection with indexes.

Registra todas las operaciones críticas sobre documentos
para trazabilidad y cumplimiento.
"""

migration_id = "008_add_audit_log"
description = "Create audit log collection for transaction demo"
author = "developer"


AUDIT_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["action", "timestamp", "document_id"],
        "properties": {
            "action": {"bsonType": "string"},
            "document_id": {"bsonType": "string"},
            "timestamp": {"bsonType": "date"},
        },
    }
}


async def up(db) -> None:
    # Idempotente: la colección puede existir ya (p. ej. creada implícitamente
    # al insertar el primer audit log desde el endpoint upload-audited).
    existing = await db.list_collection_names()
    if "audit_log" not in existing:
        await db.create_collection("audit_log", validator=AUDIT_VALIDATOR)
        print("  audit_log collection created")
    else:
        # Ya existe (probablemente sin validador): se lo aplicamos con collMod.
        await db.command("collMod", "audit_log", validator=AUDIT_VALIDATOR)
        print("  audit_log already existed; validator applied via collMod")

    # create_index es no-op si ya existe un índice con el mismo nombre y spec.
    await db["audit_log"].create_index(
        [("timestamp", -1)],
        name="idx_audit_timestamp_desc"
    )
    await db["audit_log"].create_index(
        "document_id",
        name="idx_audit_document_id"
    )
    await db["audit_log"].create_index(
        "action",
        name="idx_audit_action"
    )

    print("  audit_log indexes ensured")


async def down(db) -> None:
    await db.drop_collection("audit_log")
    print("  audit_log collection dropped")