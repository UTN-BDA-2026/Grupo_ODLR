"""
Agregar índice compuesto (owner_id, created_at) en documents.

Motivo:
El listado de documentos consulta find({"owner_id": X}).sort("created_at", ...)
(ver app/repositories/document_repo.py: get_by_owner). Hasta ahora no existía
ningún índice sobre owner_id, por lo que cada listado hacía un COLLSCAN.

Este índice compuesto resuelve dos cosas a la vez:
- El filtro por owner_id (prefijo del índice).
- El ordenamiento por created_at en ambas direcciones (asc/desc).
"""

migration_id = "011_add_owner_created_index"
description = "Add compound index (owner_id, created_at desc) on documents"
created_at = "2026-06-30T00:00:00"
author = "grupo-pdf-extract-api"


async def index_name_exists(collection, index_name: str) -> bool:
    indexes = await collection.index_information()
    return index_name in indexes


async def up(db):
    documents = db["documents"]

    if not await index_name_exists(documents, "ix_documents_owner_created"):
        await documents.create_index(
            [("owner_id", 1), ("created_at", -1)],
            name="ix_documents_owner_created",
            background=True,
        )


async def down(db):
    documents = db["documents"]

    if await index_name_exists(documents, "ix_documents_owner_created"):
        await documents.drop_index("ix_documents_owner_created")
