"""
Demo: impacto de TODOS los índices reales del proyecto (antes vs después).

Para cada índice que quedó en uso tras la auditoría, mide la MISMA query:
  - "antes": forzando COLLSCAN con hint({$natural: 1})  -> recorre toda la colección
  - "después": usando el índice real                    -> IXSCAN

Reporta, vía explain("executionStats"):
  - el stage del plan (COLLSCAN vs IXSCAN)
  - totalDocsExamined  (cuántos documentos tuvo que mirar)
  - si hubo un stage SORT en memoria (lo elimina un índice compuesto / de orden)
  - tiempo de pared promedio en ms

No toca los datos reales: trabaja sobre una colección de prueba `demo_bench`
que crea y elimina al final.

Uso (desde el host, con el stack levantado):
    uv run python scripts/demo_indexes_all.py
    uv run python scripts/demo_indexes_all.py --count 30000
"""

import argparse
import asyncio
import os
import random
import string
import sys
import time
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

# Fuerza UTF-8 en la salida para que los acentos se vean bien en Windows
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
DEMO = "demo_bench"
NUM_OWNERS = 50  # ~ NUM_DOCS / 50 documentos por owner

NATURAL_HINT = [("$natural", 1)]


def rand_str(k):
    return "".join(random.choices(string.ascii_lowercase, k=k))


def rand_dt():
    return datetime.now(timezone.utc) - timedelta(seconds=random.randint(0, 365 * 24 * 3600))


# ── helpers de medición ────────────────────────────────────────────────
def _collect_stages(plan):
    """Aplana el árbol de stages del winningPlan en una lista de nombres."""
    stages = []
    node = plan
    while node:
        name = node.get("stage")
        if name:
            stages.append(name)
        node = node.get("inputStage") or (node.get("inputStages") or [None])[0]
    return stages


async def explain(db, query, sort=None, hint=None, limit=0):
    find_cmd = {"find": DEMO, "filter": query}
    if sort:
        find_cmd["sort"] = sort
    if limit:
        find_cmd["limit"] = limit
    if hint is not None:
        find_cmd["hint"] = hint
    res = await db.command({"explain": find_cmd, "verbosity": "executionStats"})

    stages = _collect_stages(res["queryPlanner"]["winningPlan"])
    stats = res.get("executionStats", {})
    scan = "IXSCAN" if "IXSCAN" in stages else "COLLSCAN"
    return {
        "scan": scan,
        "has_sort": "SORT" in stages,
        "docs_examined": stats.get("totalDocsExamined", -1),
        "n_returned": stats.get("nReturned", -1),
    }


async def measure(col, query, sort=None, hint=None, limit=0, runs=8, warmup=2):
    async def run_once():
        cur = col.find(query)
        if sort:
            cur = cur.sort(sort)
        if limit:
            cur = cur.limit(limit)
        if hint is not None:
            cur = cur.hint(hint)
        start = time.perf_counter()
        await cur.to_list(length=None)
        return (time.perf_counter() - start) * 1000

    # Descarta las primeras corridas (caché frío) para tiempos estables
    for _ in range(warmup):
        await run_once()
    times = [await run_once() for _ in range(runs)]
    times.sort()
    # Mediana: más robusta que el promedio ante un pico aislado
    mid = len(times) // 2
    return times[mid] if len(times) % 2 else (times[mid - 1] + times[mid]) / 2


async def run_case(db, col, case):
    """Mide un caso: COLLSCAN forzado vs el índice real."""
    q, sort, limit = case["query"], case.get("sort"), case.get("limit", 0)
    idx = case["index_name"]

    before = await explain(db, q, sort=sort, hint={"$natural": 1}, limit=limit)
    after = await explain(db, q, sort=sort, hint=idx, limit=limit)

    t_before = await measure(col, q, sort=sort, hint=NATURAL_HINT, limit=limit)
    t_after = await measure(col, q, sort=sort, hint=idx, limit=limit)

    return before, after, t_before, t_after


# ── definición de los casos: 1 por índice real del proyecto ────────────
def build_cases():
    return [
        {
            "short": "documents · owner + fecha",
            "real_index": "ix_documents_owner_created {owner_id:1, created_at:-1}",
            "repo": "DocumentRepository.get_by_owner() -> GET /api/v1/pdf/",
            "index_name": "demo_owner_created",
            "index_keys": [("owner_id", 1), ("created_at", -1)],
            "query": {"owner_id": "owner_0001"},
            "sort": {"created_at": -1},
        },
        {
            "short": "documents · checksum + owner",
            "real_index": "ux_documents_checksum_owner {checksum:1, owner_id:1}",
            "repo": "DocumentRepository.find_by_checksum_and_owner() -> upload_pdf()",
            "index_name": "demo_checksum_owner",
            "index_keys": [("checksum", 1), ("owner_id", 1)],
            "query": {"checksum": "TARGET_CHK", "owner_id": "owner_target"},
        },
        {
            "short": "users · login por email",
            "real_index": "idx_users_email_unique {email:1}",
            "repo": "UserRepository.get_by_email() / email_exists()",
            "index_name": "demo_email",
            "index_keys": [("email", 1)],
            "query": {"email": "target@demo.com"},
        },
        {
            "short": "users · login por username",
            "real_index": "idx_users_username_unique {username:1}",
            "repo": "UserRepository.get_by_username() / get_by_identifier()",
            "index_name": "demo_username",
            "index_keys": [("username", 1)],
            "query": {"username": "target_user"},
        },
        {
            "short": "users · recientes x fecha",
            "real_index": "idx_users_created_at_desc {created_at:-1}",
            "repo": "listado administrativo de usuarios",
            "index_name": "demo_created",
            "index_keys": [("created_at", -1)],
            "query": {},
            "sort": {"created_at": -1},
            "limit": 20,
        },
        {
            "short": "roles · buscar por nombre",
            "real_index": "idx_roles_name_unique {name:1}",
            "repo": "RoleRepository.get_by_name()",
            "index_name": "demo_name",
            "index_keys": [("name", 1)],
            "query": {"name": "target_role"},
        },
        {
            "short": "audit_log · recientes x ts",
            "real_index": "idx_audit_timestamp_desc {timestamp:-1}",
            "repo": "AuditRepository.get_recent()",
            "index_name": "demo_timestamp",
            "index_keys": [("timestamp", -1)],
            "query": {},
            "sort": {"timestamp": -1},
            "limit": 20,
        },
    ]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50_000, help="documentos de prueba")
    args = parser.parse_args()
    num_docs = args.count

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    col = db[DEMO]

    print()
    print("=" * 78)
    print("  DEMO: impacto de los índices reales del proyecto (antes vs después)")
    print("=" * 78)

    # ── 1. Seed ────────────────────────────────────────────────────────
    print(f"\n  [1/4] Insertando {num_docs:,} documentos de prueba en '{DEMO}'...")
    await col.drop()

    actions = ["upload", "delete", "update", "summarize"]
    batch = 5_000
    for i in range(0, num_docs, batch):
        docs = [
            {
                "owner_id": f"owner_{random.randint(1, NUM_OWNERS):04d}",
                "created_at": rand_dt(),
                "timestamp": rand_dt(),
                "checksum": rand_str(32),
                "email": f"{rand_str(8)}@demo.com",
                "username": rand_str(10),
                "name": rand_str(6),
                "action": random.choice(actions),
            }
            for _ in range(batch)
        ]
        await col.insert_many(docs)
        print(f"      {min(i + batch, num_docs):,} / {num_docs:,}", end="\r")

    # Documentos "objetivo" conocidos para las queries de igualdad
    await col.insert_one(
        {
            "owner_id": "owner_target",
            "created_at": rand_dt(),
            "timestamp": rand_dt(),
            "checksum": "TARGET_CHK",
            "email": "target@demo.com",
            "username": "target_user",
            "name": "target_role",
            "action": "upload",
        }
    )
    print(f"      {num_docs:,} documentos insertados.                      ")

    # ── 2. Crear los índices de la demo ────────────────────────────────
    print("  [2/4] Creando los índices...")
    cases = build_cases()
    for c in cases:
        await col.create_index(c["index_keys"], name=c["index_name"])

    # ── 3. Medir cada caso ─────────────────────────────────────────────
    print("  [3/4] Midiendo COLLSCAN (forzado) vs IXSCAN para cada índice...\n")
    results = []
    for c in cases:
        before, after, t_before, t_after = await run_case(db, col, c)
        results.append((c, before, after, t_before, t_after))

    # ── 4. Reporte ─────────────────────────────────────────────────────
    print(f"  [4/4] Resultados sobre {num_docs:,} documentos\n")

    # Anchos de columna
    W1, W2, W3, W4 = 30, 23, 23, 9

    def sep(left, mid, right):
        return "  " + left + "─" * (W1 + 2) + mid + "─" * (W2 + 2) + mid + "─" * (
            W3 + 2
        ) + mid + "─" * (W4 + 2) + right

    def docs(n):
        return f"{n:,} doc" + ("s" if n != 1 else "")

    def cell(n, ms):
        return f"{docs(n)} · {ms:.1f} ms"

    def row(a, b, c, d):
        return f"  │ {a[:W1]:<{W1}} │ {b:>{W2}} │ {c:>{W3}} │ {d:>{W4}} │"

    print(sep("┌", "┬", "┐"))
    print(row("Consulta", "Sin índice", "Con índice", "Mejora"))
    print(row("", "(COLLSCAN)", "(IXSCAN)", "tiempo"))
    print(sep("├", "┼", "┤"))

    any_sort = False
    for c, before, after, t_before, t_after in results:
        speed = (t_before / t_after) if t_after > 0 else float("inf")
        mejora = "∞" if speed == float("inf") else f"{speed:.0f}x"
        mark = ""
        if before["has_sort"] and not after["has_sort"]:
            mark = " *"
            any_sort = True
        print(
            row(
                c["short"] + mark,
                cell(before["docs_examined"], t_before),
                cell(after["docs_examined"], t_after),
                mejora,
            )
        )
    print(sep("└", "┴", "┘"))

    # ── Leyenda: mapeo a los índices reales del proyecto ───────────────
    print("\n  Cada fila mapea a un índice real del proyecto:\n")
    for c, before, after, t_before, t_after in results:
        mark = " *" if (before["has_sort"] and not after["has_sort"]) else ""
        print(f"  • {c['short']}{mark:<2} -> {c['real_index']}")
    if any_sort:
        print("\n  (*) Además del filtro, el índice evita ordenar en memoria (elimina el stage SORT).")
    print("\n  'docs' = documentos que MongoDB tuvo que leer (totalDocsExamined).")

    # ── Limpieza ───────────────────────────────────────────────────────
    print()
    await col.drop()
    print("  (colección de demo eliminada)\n")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
