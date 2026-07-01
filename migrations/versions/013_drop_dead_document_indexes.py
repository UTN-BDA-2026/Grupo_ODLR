"""
Eliminar índices muertos en la colección documents.

Motivo (verificado contra queries reales en app/repositories y la API):
- idx_filename          -> la búsqueda por nombre usa $regex no anclado, que no
                           aprovecha un índice B-tree; corre acotada por owner_id.
- idx_created_at_desc   -> reemplazado por el compuesto ix_documents_owner_created
                           (migración 011), que cubre filtro por owner + sort.
- idx_status_created_at -> índice fantasma: el campo "status" no existe en el
                           modelo DocumentDocument.
- idx_user_id           -> las queries usan owner_id, nunca user_id.
- idx_organization_id   -> ninguna query filtra por organization_id.
- idx_user_created      -> idem: user_id no se consulta.
- idx_docs_summary_exists -> ninguna query filtra por summary.
- ux_documents_checksum -> reemplazado por ux_documents_checksum_owner (010);
                           normalmente ya no existe. NO se restaura en down()
                           porque su unicidad sobre checksum solo entra en
                           conflicto con la regla actual (checksum + owner_id).
"""

migration_id = "013_drop_dead_document_indexes"
description = "Drop unused/ghost indexes on documents collection"
created_at = "2026-06-30T00:02:00"
author = "grupo-pdf-extract-api"


# (nombre, key, opciones) para poder restaurar en down()
DEAD_INDEXES = [
    ("idx_filename", [("filename", 1)], {}),
    ("idx_created_at_desc", [("created_at", -1)], {}),
    ("idx_status_created_at", [("status", 1), ("created_at", -1)], {}),
    ("idx_user_id", [("user_id", 1)], {"sparse": True}),
    ("idx_organization_id", [("organization_id", 1)], {"sparse": True}),
    ("idx_user_created", [("user_id", 1), ("created_at", -1)], {}),
    ("idx_docs_summary_exists", [("summary", 1)], {"sparse": True}),
]

# Se elimina si quedó, pero no se restaura (ver docstring).
LEGACY_UNIQUE_CHECKSUM = "ux_documents_checksum"


async def index_name_exists(collection, index_name: str) -> bool:
    indexes = await collection.index_information()
    return index_name in indexes


async def up(db):
    documents = db["documents"]

    for name, _key, _opts in DEAD_INDEXES:
        if await index_name_exists(documents, name):
            await documents.drop_index(name)

    if await index_name_exists(documents, LEGACY_UNIQUE_CHECKSUM):
        await documents.drop_index(LEGACY_UNIQUE_CHECKSUM)


async def down(db):
    documents = db["documents"]

    for name, key, opts in DEAD_INDEXES:
        if not await index_name_exists(documents, name):
            await documents.create_index(key, name=name, background=True, **opts)
