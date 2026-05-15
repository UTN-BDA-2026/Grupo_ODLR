# tests/conftest.py

import pytest
import fitz
from app.db.database import db as mongo_db


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Genera un PDF mínimo en memoria para los tests."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Hola mundo desde el PDF de prueba")
    return doc.tobytes()


# ✅ Fixture nuevo para el test de conexión real
@pytest.fixture
async def database_connection():
    """Provee conexión real a MongoDB para integration tests."""
    await mongo_db.connect()
    yield mongo_db
    await mongo_db.disconnect()