"""
Demo: COLLSCAN vs IXSCAN — tiempos reales

Inserta N documentos falsos, mide la misma query sin índice y con índice,
y muestra la diferencia en milisegundos para la defensa.
"""

import asyncio
import os
import sys
import time
import random
import string
from motor.motor_asyncio import AsyncIOMotorClient

# Fuerza UTF-8 en la salida para que los acentos se muestren bien en Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_raw_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
# Reemplaza el hostname Docker por localhost cuando corre fuera del contenedor
MONGODB_URL = _raw_url.replace("mongodb://mongodb:", "mongodb://localhost:")
# directConnection=true evita que el driver siga el hostname del replica set
if "directConnection" not in MONGODB_URL:
    sep = "&" if "?" in MONGODB_URL else "?"
    MONGODB_URL = MONGODB_URL + sep + "directConnection=true"
DB_NAME = "pdf_extract_db"
DEMO_COLLECTION = "demo_bench"
NUM_DOCS = 50_000  # suficiente para ver diferencia real


def random_email():
    user = "".join(random.choices(string.ascii_lowercase, k=8))
    domain = random.choice(["gmail.com", "yahoo.com", "hotmail.com", "utn.edu.ar"])
    return f"{user}@{domain}"


def random_filename():
    name = "".join(random.choices(string.ascii_lowercase, k=10))
    return f"{name}.pdf"


async def measure(collection, query, runs=5):
    """Ejecuta la query N veces y devuelve el promedio en ms."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        cursor = collection.find(query)
        await cursor.to_list(length=1)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return sum(times) / len(times)


async def get_stage(collection, query):
    result = await collection.find(query).explain()
    plan = result["queryPlanner"]["winningPlan"]
    stage = plan.get("stage", "")
    if stage in ("FETCH", "PROJECTION_DEFAULT", "PROJECTION_SIMPLE"):
        stage = plan.get("inputStage", {}).get("stage", stage)
    return stage


async def main():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    col = db[DEMO_COLLECTION]

    print()
    print("=" * 60)
    print("  DEMO: Índices — impacto real en tiempos de consulta")
    print("=" * 60)

    # ── 1. Seed ──────────────────────────────────────────────────
    print(f"\n  [1/4] Insertando {NUM_DOCS:,} documentos de prueba...")
    await col.drop()

    batch_size = 5_000
    for i in range(0, NUM_DOCS, batch_size):
        docs = [
            {
                "email": random_email(),
                "filename": random_filename(),
                "status": random.choice(["active", "inactive"]),
                "size": random.randint(1000, 5_000_000),
            }
            for _ in range(batch_size)
        ]
        await col.insert_many(docs)
        print(f"      {min(i + batch_size, NUM_DOCS):,} / {NUM_DOCS:,}", end="\r")

    # Fijar un documento conocido para buscar
    target_email = "target@demo.com"
    target_filename = "target_document.pdf"
    await col.insert_one({"email": target_email, "filename": target_filename, "status": "active"})
    print(f"      {NUM_DOCS:,} documentos insertados.          ")

    # ── 2. Sin índice (COLLSCAN) ──────────────────────────────────
    print("\n  [2/4] Midiendo sin índice (COLLSCAN)...")
    await col.drop_indexes()

    query_email = {"email": target_email}
    query_file = {"filename": target_filename}

    stage_no_idx_email = await get_stage(col, query_email)
    stage_no_idx_file = await get_stage(col, query_file)

    time_no_email = await measure(col, query_email)
    time_no_file = await measure(col, query_file)

    # ── 3. Crear índices ──────────────────────────────────────────
    print("  [3/4] Creando índices...")
    await col.create_index("email", name="idx_demo_email")
    await col.create_index("filename", name="idx_demo_filename")

    stage_idx_email = await get_stage(col, query_email)
    stage_idx_file = await get_stage(col, query_file)

    time_with_email = await measure(col, query_email)
    time_with_file = await measure(col, query_file)

    # ── 4. Resultados ─────────────────────────────────────────────
    print("  [4/4] Resultados\n")
    print(f"  {'Colección de prueba:':<30} {NUM_DOCS:,} documentos")
    print()

    def speedup(without, with_idx):
        if with_idx == 0:
            return "∞"
        x = without / with_idx
        return f"{x:.0f}x más rápido"

    rows = [
        ("Búsqueda por email", stage_no_idx_email, time_no_email, stage_idx_email, time_with_email),
        ("Búsqueda por filename", stage_no_idx_file, time_no_file, stage_idx_file, time_with_file),
    ]

    header = f"  {'Query':<25} {'Sin índice':>18}   {'Con índice':>18}   {'Mejora':>16}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for label, s_no, t_no, s_yes, t_yes in rows:
        no_str = f"{t_no:6.2f} ms ({s_no})"
        yes_str = f"{t_yes:6.2f} ms ({s_yes})"
        sp = speedup(t_no, t_yes)
        print(f"  {label:<25} {no_str:>18}   {yes_str:>18}   {sp:>16}")

    print()
    print("  Conclusión:")
    for label, _, t_no, _, t_yes in rows:
        sp = t_no / t_yes if t_yes > 0 else float("inf")
        print(f"  * {label}: {t_no:.2f} ms -> {t_yes:.2f} ms  ({sp:.0f}x de mejora)")

    # ── Limpieza ──────────────────────────────────────────────────
    print()
    await col.drop()
    print("  (colección de demo eliminada)")
    print()

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
