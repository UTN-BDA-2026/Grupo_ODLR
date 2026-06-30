"""
Seed: crea 4 usuarios fijos e inserta documentos distribuidos entre ellos.

Uso:
    uv run python scripts/seed_documents.py
    uv run python scripts/seed_documents.py --count 200   # cantidad personalizada
"""

import asyncio
import hashlib
import os
import random
import sys
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SEED_USERS = [
    {"username": "admin",   "email": "admin@demo.com",   "password": "admin123",   "full_name": "Admin"},
    {"username": "usuario", "email": "usuario@demo.com", "password": "usuario123", "full_name": "Usuario Demo"},
    {"username": "santino", "email": "santino@demo.com", "password": "santino123", "full_name": "Santino"},
    {"username": "juani",   "email": "juani@demo.com",   "password": "juani123",   "full_name": "Juani"},
]

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
if "directConnection" not in MONGODB_URL:
    sep = "&" if "?" in MONGODB_URL else "?"
    MONGODB_URL = MONGODB_URL + sep + "directConnection=true"

DB_NAME = "pdf_extract_db"

TEMAS = [
    "informe", "resumen", "contrato", "acta", "factura",
    "presupuesto", "manual", "reporte", "analisis", "propuesta",
]
AREAS = [
    "ventas", "rrhh", "legal", "finanzas", "it",
    "logistica", "marketing", "operaciones", "auditoria", "compras",
]
TEXTOS = [
    "Este documento contiene informacion sobre los resultados obtenidos durante el periodo analizado.",
    "Se detallan los procedimientos a seguir para la correcta ejecucion del proceso.",
    "El presente informe resume las actividades realizadas y los objetivos cumplidos.",
    "Se adjuntan los datos estadisticos correspondientes al trimestre en curso.",
    "Este contrato establece los terminos y condiciones acordados entre las partes.",
    "El analisis presentado refleja el estado actual del area evaluada.",
    "Se incluyen las recomendaciones surgidas del proceso de auditoria interna.",
    "Los indicadores de gestion muestran una mejora sostenida respecto al periodo anterior.",
    "La presente propuesta detalla el alcance y los entregables del proyecto.",
    "Este manual describe paso a paso el uso correcto del sistema.",
]


async def ensure_seed_users(db) -> list[str]:
    """Crea los usuarios de seed si no existen; devuelve sus IDs como strings."""
    now = datetime.now(timezone.utc)
    owner_ids = []

    for u in SEED_USERS:
        existing = await db["users"].find_one({"username": u["username"]})
        if existing:
            owner_ids.append(str(existing["_id"]))
            print(f"  [skip]   {u['username']} ya existe")
        else:
            result = await db["users"].insert_one({
                "username": u["username"],
                "email": u["email"],
                "hashed_password": pwd_context.hash(u["password"]),
                "full_name": u["full_name"],
                "is_active": True,
                "is_superuser": u["username"] == "admin",
                "role_ids": [],
                "created_at": now,
                "updated_at": now,
            })
            owner_ids.append(str(result.inserted_id))
            print(f"  [creado] {u['username']} / {u['password']}")

    return owner_ids


def fake_doc(index: int, owner_ids: list) -> dict:
    tema = random.choice(TEMAS)
    area = random.choice(AREAS)
    year = random.randint(2022, 2025)
    month = random.randint(1, 12)
    filename = f"{tema}_{area}_{year}_{index:04d}.pdf"
    text = random.choice(TEXTOS) + f" Documento numero {index}."
    checksum = hashlib.sha256(f"{filename}{index}".encode()).hexdigest()
    created = datetime(year, month, random.randint(1, 28),
                       random.randint(8, 18), random.randint(0, 59))
    return {
        "filename": filename,
        "text": text,
        "checksum": checksum,
        "owner_id": random.choice(owner_ids),
        "created_at": created,
        "updated_at": created + timedelta(minutes=random.randint(0, 60)),
    }


async def main(count: int = 50_000):
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    col = db["documents"]

    print("\nCreando/verificando usuarios de seed...")
    owner_ids = await ensure_seed_users(db)
    print(f"Usuarios listos: {len(owner_ids)}\n")

    existing = await col.count_documents({})
    print(f"Documentos actuales en la coleccion: {existing}")
    print(f"Insertando {count} documentos distribuidos entre {len(owner_ids)} usuarios...\n")

    docs = [fake_doc(existing + i + 1, owner_ids) for i in range(count)]

    batch_size = 500
    inserted = 0
    for i in range(0, count, batch_size):
        batch = docs[i : i + batch_size]
        result = await col.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
        print(f"  {inserted}/{count} insertados", end="\r")

    total = await col.count_documents({})
    print(f"\n  {inserted} documentos insertados correctamente.")
    print(f"  Total en la coleccion ahora: {total}\n")

    client.close()


if __name__ == "__main__":
    count = 50_000
    if "--count" in sys.argv:
        idx = sys.argv.index("--count")
        count = int(sys.argv[idx + 1])
    asyncio.run(main(count))
