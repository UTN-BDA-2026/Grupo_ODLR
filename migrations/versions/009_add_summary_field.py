"""
Add summary field to documents collection.
"""

migration_id = "009_add_summary_field"
description = "Add summary field and index to documents collection"
author = "developer"


async def up(db):
    # Agrega summary: null a todos los docs que no lo tienen
    await db["documents"].update_many(
        {"summary": {"$exists": False}},
        {"$set": {"summary": None}}
    )
    # Índice para buscar docs con/sin resumen
    await db["documents"].create_index(
        [("summary", 1)],
        name="idx_docs_summary_exists",
        sparse=True,
    )


async def down(db):
    await db["documents"].update_many(
        {}, {"$unset": {"summary": ""}}
    )
    await db["documents"].drop_index("idx_docs_summary_exists")