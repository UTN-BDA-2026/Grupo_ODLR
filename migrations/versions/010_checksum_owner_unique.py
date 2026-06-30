"""
Cambiar unicidad de checksum a (checksum, owner_id).

Permite que distintos usuarios suban el mismo PDF,
pero impide que un mismo usuario lo suba dos veces.
"""

migration_id = "010_checksum_owner_unique"
description = "Replace unique checksum index with compound (checksum, owner_id) unique index"
created_at = "2026-06-25T00:00:00"
author = "grupo-pdf-extract-api"


async def up(db):
    documents = db["documents"]
    indexes = await documents.index_information()

    # Dropear el índice único anterior (solo checksum)
    for name, info in indexes.items():
        key_fields = [f for f, _ in info.get("key", [])]
        if key_fields == ["checksum"] and info.get("unique"):
            await documents.drop_index(name)
            break

    # Crear índice compuesto único (checksum, owner_id)
    await documents.create_index(
        [("checksum", 1), ("owner_id", 1)],
        unique=True,
        name="ux_documents_checksum_owner",
        background=True,
    )


async def down(db):
    documents = db["documents"]
    indexes = await documents.index_information()

    if "ux_documents_checksum_owner" in indexes:
        await documents.drop_index("ux_documents_checksum_owner")

    # Restaurar índice único solo sobre checksum
    await documents.create_index(
        [("checksum", 1)],
        unique=True,
        name="ux_documents_checksum",
        background=True,
    )
