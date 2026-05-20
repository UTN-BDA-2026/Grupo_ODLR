"""
Backup script for MongoDB database.

Ejecuta mongodump dentro del container Docker y guarda
el backup en ./backups/<timestamp>/

Uso:
    python scripts/backup.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


CONTAINER_NAME = "grupo_odlr-mongodb-1"
DB_NAME = "pdf_extract_db"
BACKUP_BASE_DIR = Path("backups")


def run_backup() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_BASE_DIR / timestamp

    # Crear directorio local
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando backup: {timestamp}")
    print(f"Base de datos: {DB_NAME}")
    print(f"Destino: {backup_dir}/")
    print("-" * 45)

    # Ejecutar mongodump dentro del container
    # El output se guarda en /tmp/backup dentro del container
    # y después lo copiamos al host con docker cp
    cmd_dump = [
        "docker", "exec", CONTAINER_NAME,
        "mongodump",
        f"--db={DB_NAME}",
        f"--out=/tmp/backup_{timestamp}",
        "--gzip",
    ]

    result = subprocess.run(cmd_dump, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR en mongodump:\n{result.stderr}")
        sys.exit(1)

    print(result.stderr)  # mongodump imprime progreso en stderr

    # Copiar backup del container al host
    cmd_cp = [
        "docker", "cp",
        f"{CONTAINER_NAME}:/tmp/backup_{timestamp}/{DB_NAME}",
        str(backup_dir),
    ]

    result = subprocess.run(cmd_cp, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR copiando backup:\n{result.stderr}")
        sys.exit(1)

    # Limpiar directorio temporal dentro del container
    subprocess.run([
        "docker", "exec", CONTAINER_NAME,
        "rm", "-rf", f"/tmp/backup_{timestamp}"
    ])

    # Escribir manifest
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        f'{{"timestamp": "{timestamp}", "database": "{DB_NAME}"}}\n'
    )

    print("-" * 45)
    print(f"Backup completado: {backup_dir}/")

    # Listar archivos generados
    for f in sorted((backup_dir / DB_NAME).iterdir()):
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    run_backup()