"""
Demo: COLLSCAN vs IXSCAN con explain()

Muestra cómo MongoDB usa los índices creados en la migración 007
para resolver queries en O(log n) en lugar de O(n).
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "pdf_extract_db"


async def get_stage(collection, query):
    """Retorna el stage del plan ganador (COLLSCAN o IXSCAN)."""
    result = await collection.find(query).explain()
    stage = result["queryPlanner"]["winningPlan"].get("stage", "")
    # En planes con FETCH el IXSCAN está un nivel adentro
    if stage == "FETCH":
        stage = result["queryPlanner"]["winningPlan"]["inputStage"].get("stage", stage)
    return stage


async def main():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    print()
    print("=" * 55)
    print("  DEMO: explain() - COLLSCAN vs IXSCAN")
    print("=" * 55)
    print()

    checks = [
        {
            "label": "Detección de PDF duplicado",
            "collection": db["documents"],
            "query": {"checksum": "abc123"},
        },
        {
            "label": "Búsqueda por filename",
            "collection": db["documents"],
            "query": {"filename": "test.pdf"},
        },
        {
            "label": "Login por email",
            "collection": db["users"],
            "query": {"email": "admin@test.com"},
        },
    ]

    all_ok = True
    for check in checks:
        stage = await get_stage(check["collection"], check["query"])
        if "IXSCAN" in stage:
            icon = "✓"
            detail = f"Stage: IXSCAN — O(log n) — acceso directo"
        else:
            icon = "✗"
            detail = f"Stage: {stage} — índice no utilizado"
            all_ok = False

        print(f"  [{icon}] {check['label']}")
        print(f"      {detail}")
        print()

    if all_ok:
        print("  Todos los índices están siendo utilizados correctamente.")
    else:
        print("  ADVERTENCIA: Algunas queries no están usando índices.")
    print()

    client.close()


if __name__ == "__main__":
    asyncio.run(main())