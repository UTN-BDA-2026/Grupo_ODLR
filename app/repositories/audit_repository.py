"""
Audit log repository.

Persiste eventos de auditoría para trazabilidad de operaciones críticas.
"""

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase


class AuditRepository:

    collection_name = "audit_log"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.collection_name]

    async def log(
        self,
        action: str,
        document_id: str,
        filename: str,
        checksum: str,
        session: AsyncIOMotorClientSession | None = None,
    ) -> None:
        """
        Registra un evento de auditoría.

        El parámetro session permite que este insert sea parte
        de una transacción atómica con otras operaciones.
        Si session es None, se ejecuta fuera de transacción.
        """
        entry = {
            "action": action,
            "document_id": document_id,
            "filename": filename,
            "checksum": checksum,
            "timestamp": datetime.now(timezone.utc),
        }
        await self.collection.insert_one(entry, session=session)

    async def get_recent(self, limit: int = 50) -> list[dict]:
        cursor = self.collection.find({}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)