"""
Create audit log collection with indexes.

Registra todas las operaciones críticas sobre documentos
para trazabilidad y cumplimiento.
"""

migration_id = "008_add_audit_log"
description = "Create audit log collection for transaction demo"
author = "developer"


async def up(db) -> None:
    # Crear colección con validación de schema
    await db.create_collection(
        "audit_log",
        validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["action", "timestamp", "document_id"],
                "properties": {
                    "action": {"bsonType": "string"},
                    "document_id": {"bsonType": "string"},
                    "timestamp": {"bsonType": "date"},
                }
            }
        }
    )

    # Índice para consultas por fecha (más reciente primero)
    await db["audit_log"].create_index(
        [("timestamp", -1)],
        name="idx_audit_timestamp_desc"
    )

    # Índice para consultas por documento
    await db["audit_log"].create_index(
        "document_id",
        name="idx_audit_document_id"
    )

    # Índice para consultas por acción
    await db["audit_log"].create_index(
        "action",
        name="idx_audit_action"
    )

    print("  audit_log collection created with indexes")


async def down(db) -> None:
    await db.drop_collection("audit_log")
    print("  audit_log collection dropped")