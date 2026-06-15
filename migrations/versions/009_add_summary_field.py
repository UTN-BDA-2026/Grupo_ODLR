from migrations.base import BaseMigration

class Migration(BaseMigration):
    version = "009"
    description = "Add summary field to documents collection"

    async def up(self):
        # Agrega summary: null a todos los docs que no lo tienen
        await self.db["documents"].update_many(
            {"summary": {"$exists": False}},
            {"$set": {"summary": None}}
        )
        # Índice para buscar docs con/sin resumen
        await self.db["documents"].create_index(
            [("summary", 1)],
            name="idx_docs_summary_exists",
            sparse=True,
        )
        self.log("Campo 'summary' e índice agregados")

    async def down(self):
        await self.db["documents"].update_many(
            {}, {"$unset": {"summary": ""}}
        )
        await self.db["documents"].drop_index("idx_docs_summary_exists")