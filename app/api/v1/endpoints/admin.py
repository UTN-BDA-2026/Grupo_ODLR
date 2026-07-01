"""
Admin endpoints for backup and maintenance operations.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.endpoints.auth import require_superuser
from app.db.database import get_db_session
from app.schemas.document import DocumentResponse
from app.schemas.user import UserResponse
from app.services.document_service import document_service
from app.services.user_service import user_service

router = APIRouter(tags=["admin"])

CONTAINER_NAME = "grupo_odlr-mongodb-1"
DB_NAME = "pdf_extract_db"
BACKUP_BASE_DIR = Path("backups")


@router.post("/backup", summary="Trigger manual database backup")
async def trigger_backup(
    current_user=Depends(require_superuser),
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_BASE_DIR / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Dump dentro del container
    result = subprocess.run(
        [
            "docker", "exec", CONTAINER_NAME,
            "mongodump",
            f"--db={DB_NAME}",
            f"--out=/tmp/backup_{timestamp}",
            "--gzip",
        ],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    # Copiar al host
    subprocess.run([
        "docker", "cp",
        f"{CONTAINER_NAME}:/tmp/backup_{timestamp}/{DB_NAME}",
        str(backup_dir),
    ])

    # Limpiar temporal
    subprocess.run([
        "docker", "exec", CONTAINER_NAME,
        "rm", "-rf", f"/tmp/backup_{timestamp}"
    ])

    # Manifest
    (backup_dir / "manifest.json").write_text(
        f'{{"timestamp": "{timestamp}", "database": "{DB_NAME}"}}\n'
    )

    return {
        "status": "success",
        "backup_id": timestamp,
        "path": str(backup_dir),
    }


@router.get("/backups", summary="List available backups")
async def list_backups(
    current_user=Depends(require_superuser),
):
    if not BACKUP_BASE_DIR.exists():
        return {"backups": []}

    backups = sorted([
        d.name for d in BACKUP_BASE_DIR.iterdir()
        if d.is_dir() and (d / DB_NAME).exists()
    ], reverse=True)

    return {"backups": backups, "total": len(backups)}


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (admin)",
    description="Listado de todos los usuarios ordenado por fecha de alta "
                "(usa el índice idx_users_created_at_desc).",
)
async def admin_list_users(
    skip: int = 0,
    limit: int = 0,
    order: str = "desc",
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(require_superuser),
) -> List[UserResponse]:
    return await user_service.list_users_admin(
        session, skip=skip, limit=limit, order=order
    )


@router.get(
    "/documents",
    response_model=List[DocumentResponse],
    summary="List all documents (admin)",
    description="Listado de documentos de todos los usuarios. Filtrando por "
                "owner_id usa el índice ix_documents_owner_created.",
)
async def admin_list_documents(
    owner_id: str | None = None,
    search: str | None = None,
    order: str = "desc",
    skip: int = 0,
    limit: int = 0,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(require_superuser),
) -> List[DocumentResponse]:
    return await document_service.list_all_documents(
        session, owner_id=owner_id, search=search, order=order, skip=skip, limit=limit
    )


@router.get(
    "/stats",
    summary="Global counters (admin)",
    description="Totales de usuarios y documentos para el panel administrativo.",
)
async def admin_stats(
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(require_superuser),
):
    return {
        "total_users": await user_service.count_users(session),
        "total_documents": await document_service.count_documents(session),
    }