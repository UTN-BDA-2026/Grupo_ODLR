"""
Add additional database indexes.

Tema implementado:
- Indices personalizados en MongoDB.
- Indices unicos para integridad de datos.
- Indices adicionales para consultas frecuentes.

Nota:
El proyecto ya tenia algunos indices creados por migraciones anteriores.
Por eso esta migracion verifica indices existentes por campo y no solo por nombre.
"""

migration_id = "007_add_database_indexes"
description = "Add additional database indexes"
created_at = "2026-05-19T00:00:00"
author = "grupo-pdf-extract-api"


async def index_name_exists(collection, index_name: str) -> bool:
    indexes = await collection.index_information()
    return index_name in indexes


async def index_key_exists(collection, expected_key: list[tuple[str, int]]) -> bool:
    """
    Verifica si ya existe un índice con los mismos campos y dirección,
    aunque tenga otro nombre.
    """
    indexes = await collection.index_information()

    for index_data in indexes.values():
        current_key = index_data.get("key")
        if current_key == expected_key:
            return True

    return False


async def unique_index_key_exists(collection, expected_key: list[tuple[str, int]]) -> bool:
    """
    Verifica si ya existe un índice único con los mismos campos y dirección,
    aunque tenga otro nombre.
    """
    indexes = await collection.index_information()

    for index_data in indexes.values():
        current_key = index_data.get("key")
        is_unique = index_data.get("unique") is True

        if current_key == expected_key and is_unique:
            return True

    return False


async def up(db):
    documents = db["documents"]
    users = db["users"]

    # Evita guardar dos veces el mismo PDF.
    # Solo se crea si no existe ya un índice único sobre checksum.
    if not await unique_index_key_exists(documents, [("checksum", 1)]):
        await documents.create_index(
            [("checksum", 1)],
            unique=True,
            name="ux_documents_checksum",
            background=True,
        )

    # Evita duplicar usuarios por email.
    # En algunas bases ya existe como idx_users_email_unique.
    if not await unique_index_key_exists(users, [("email", 1)]):
        await users.create_index(
            [("email", 1)],
            unique=True,
            name="ux_users_email",
            background=True,
        )

    # Evita duplicar usuarios por username.
    if not await unique_index_key_exists(users, [("username", 1)]):
        await users.create_index(
            [("username", 1)],
            unique=True,
            name="ux_users_username",
            background=True,
        )

    # Mejora listados administrativos de usuarios recientes.
    if not await index_key_exists(users, [("created_at", -1)]):
        await users.create_index(
            [("created_at", -1)],
            name="ix_users_created_at_desc",
            background=True,
        )


async def down(db):
    documents = db["documents"]
    users = db["users"]

    # Solo eliminamos índices cuyo nombre pertenece a esta migración.
    # No eliminamos índices antiguos como idx_users_email_unique porque
    # probablemente fueron creados por otra migración.

    for index_name in [
        "ux_documents_checksum",
    ]:
        if await index_name_exists(documents, index_name):
            await documents.drop_index(index_name)

    for index_name in [
        "ux_users_email",
        "ux_users_username",
        "ix_users_created_at_desc",
    ]:
        if await index_name_exists(users, index_name):
            await users.drop_index(index_name)