# app/services/ollama_service.py
import httpx
from app.core.config import settings


class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    async def summarize(self, text: str) -> str:
        truncated = text[:3000]
        prompt = (
            "Analizá el siguiente texto y generá un resumen detallado en español. "
            "Incluí: (1) tema principal, (2) puntos clave en 5-7 oraciones, "
            "(3) conclusión. Solo devolvé el resumen estructurado.\n\n"
            f"Texto:\n{truncated}"
        )
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()


ollama_service = OllamaService()