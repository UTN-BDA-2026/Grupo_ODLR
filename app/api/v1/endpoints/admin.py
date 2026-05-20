"""
Admin endpoints for backup and maintenance operations.
"""

import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

CONTAINER_NAME = "grupo_odlr-mongodb-1"
DB_NAME = "pdf_extract_db"
BACKUP_BASE_DIR = Path("backups")


@router.post("/backup", summary="Trigger manual database backup")
async def trigger_backup(
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
):
    if not BACKUP_BASE_DIR.exists():
        return {"backups": []}

    backups = sorted([
        d.name for d in BACKUP_BASE_DIR.iterdir()
        if d.is_dir() and (d / DB_NAME).exists()
    ], reverse=True)

    return {"backups": backups, "total": len(backups)}