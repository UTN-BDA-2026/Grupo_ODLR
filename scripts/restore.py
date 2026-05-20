"""
Restore script for MongoDB database.

Ejecuta mongorestore dentro del container Docker desde
un backup previamente generado por backup.py

Uso:
    python scripts/restore.py                    # restaura el más reciente
    python scripts/restore.py 20250519_160844    # restaura uno específico
"""

import subprocess
import sys
from pathlib import Path


CONTAINER_NAME = "grupo_odlr-mongodb-1"
DB_NAME = "pdf_extract_db"
BACKUP_BASE_DIR = Path("backups")


def list_backups() -> list[Path]:
    if not BACKUP_BASE_DIR.exists():
        return []
    return sorted([
        d for d in BACKUP_BASE_DIR.iterdir()
        if d.is_dir() and (d / DB_NAME).exists()
    ])


def run_restore(timestamp: str | None = None) -> None:
    backups = list_backups()

    if not backups:
        print("No hay backups disponibles en ./backups/")
        sys.exit(1)

    # Seleccionar backup
    if timestamp:
        matches = [b for b in backups if b.name == timestamp]
        if not matches:
            print(f"No se encontró el backup: {timestamp}")
            print("Backups disponibles:")
            for b in backups:
                print(f"  {b.name}")
            sys.exit(1)
        backup_dir = matches[0]
    else:
        backup_dir = backups[-1]  # el más reciente
        print(f"Usando backup más reciente: {backup_dir.name}")

    source_dir = backup_dir / DB_NAME

    print(f"\nRestaurando backup: {backup_dir.name}")
    print(f"Base de datos destino: {DB_NAME}")
    print("ADVERTENCIA: Esto reemplaza los datos actuales (--drop)")
    print("-" * 45)

    # Confirmar
    confirm = input("Continuar? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        sys.exit(0)

    # Copiar backup al container
    cmd_cp = [
        "docker", "cp",
        str(source_dir),
        f"{CONTAINER_NAME}:/tmp/restore_{backup_dir.name}",
    ]

    result = subprocess.run(cmd_cp, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR copiando al container:\n{result.stderr}")
        sys.exit(1)

    # Ejecutar mongorestore dentro del container
    cmd_restore = [
        "docker", "exec", CONTAINER_NAME,
        "mongorestore",
        f"--db={DB_NAME}",
        "--drop",
        "--gzip",
        f"/tmp/restore_{backup_dir.name}",
    ]

    result = subprocess.run(cmd_restore, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR en mongorestore:\n{result.stderr}")
        sys.exit(1)

    print(result.stderr)

    # Limpiar temporal en el container
    subprocess.run([
        "docker", "exec", CONTAINER_NAME,
        "rm", "-rf", f"/tmp/restore_{backup_dir.name}"
    ])

    print("-" * 45)
    print(f"Restauración completada desde: {backup_dir.name}")


if __name__ == "__main__":
    timestamp_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_restore(timestamp_arg)