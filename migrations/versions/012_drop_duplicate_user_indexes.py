"""
Eliminar índices duplicados en la colección users.

Motivo:
La migración 005 creó idx_users_email_unique, idx_users_username_unique e
idx_users_created_at_desc. La migración 007 intentó crear equivalentes
(ux_users_email, ux_users_username, ix_users_created_at_desc). La 007 tiene
guards, por lo que estos duplicados pueden no existir; esta migración es
idempotente y solo elimina los que efectivamente estén presentes.

Se conservan los índices originales de la migración 005.
"""

migration_id = "012_drop_duplicate_user_indexes"
description = "Drop duplicate user indexes left by migration 007"
created_at = "2026-06-30T00:01:00"
author = "grupo-pdf-extract-api"


DUPLICATE_INDEXES = [
    # (nombre duplicado de 007, definición de la key para poder restaurarlo)
    ("ux_users_email", [("email", 1)], {"unique": True}),
    ("ux_users_username", [("username", 1)], {"unique": True}),
    ("ix_users_created_at_desc", [("created_at", -1)], {}),
]


async def index_name_exists(collection, index_name: str) -> bool:
    indexes = await collection.index_information()
    return index_name in indexes


async def up(db):
    users = db["users"]

    for name, _key, _opts in DUPLICATE_INDEXES:
        if await index_name_exists(users, name):
            await users.drop_index(name)


async def down(db):
    users = db["users"]

    # Restaura los índices de la migración 007 solo si no existen ya
    # (los equivalentes de la 005 siguen presentes de todos modos).
    for name, key, opts in DUPLICATE_INDEXES:
        if not await index_name_exists(users, name):
            await users.create_index(key, name=name, background=True, **opts)
