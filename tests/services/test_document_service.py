import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

os.environ["DEBUG"] = "true"

from app.core.exceptions import ConflictException, NotFoundException
from app.models.document import DocumentDocument
from app.schemas.document import DocumentUpdate
from app.services.document_service import DocumentService

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"
NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def document_service() -> DocumentService:
    return DocumentService()


@pytest.fixture
def sample_document() -> DocumentDocument:
    return DocumentDocument(
        id=VALID_OBJECT_ID,
        filename="archivo.pdf",
        text="Texto extraído",
        checksum="abc123sha256",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def mock_collection():
    col = MagicMock()
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(VALID_OBJECT_ID)))
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.count_documents = AsyncMock(return_value=0)
    cursor = MagicMock()
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    col.find = MagicMock(return_value=cursor)
    return col


@pytest.fixture
def mock_db(mock_collection):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


# --- upload_pdf ---

@pytest.mark.asyncio
async def test_upload_pdf_creates_and_returns_response(document_service, mock_db, mock_collection):
    inserted_doc = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "filename": "archivo.pdf",
        "text": "Texto extraído",
        "checksum": "sha256-checksum",
        "created_at": NOW,
        "updated_at": NOW,
    }
    mock_collection.find_one = AsyncMock(side_effect=[None, inserted_doc])

    with (
        patch("app.services.document_service.calculate_checksum", return_value="sha256-checksum"),
        patch("app.services.document_service.extract_text_from_bytes", return_value="Texto extraído"),
    ):
        result = await document_service.upload_pdf(mock_db, b"%PDF-fake", "archivo.pdf")

    assert result.id == VALID_OBJECT_ID
    assert result.filename == "archivo.pdf"
    assert result.checksum == "sha256-checksum"


@pytest.mark.asyncio
async def test_upload_pdf_raises_conflict_if_duplicate_checksum(document_service, mock_db, mock_collection):
    existing = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "filename": "archivo.pdf",
        "text": "Texto",
        "checksum": "sha256-checksum",
        "created_at": NOW,
        "updated_at": NOW,
    }
    mock_collection.find_one = AsyncMock(return_value=existing)

    with (
        patch("app.services.document_service.calculate_checksum", return_value="sha256-checksum"),
        patch("app.services.document_service.extract_text_from_bytes", return_value="Texto"),
    ):
        with pytest.raises(ConflictException, match="ya existe"):
            await document_service.upload_pdf(mock_db, b"%PDF-fake", "archivo.pdf")


# --- get_document_by_id ---

@pytest.mark.asyncio
async def test_get_document_by_id_returns_response(document_service, mock_db, mock_collection):
    mock_collection.find_one = AsyncMock(return_value={
        "_id": ObjectId(VALID_OBJECT_ID),
        "filename": "archivo.pdf",
        "text": "Texto",
        "checksum": "abc123",
        "created_at": NOW,
        "updated_at": NOW,
    })

    result = await document_service.get_document_by_id(mock_db, VALID_OBJECT_ID)

    assert result.id == VALID_OBJECT_ID
    assert result.filename == "archivo.pdf"


@pytest.mark.asyncio
async def test_get_document_by_id_raises_not_found(document_service, mock_db, mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await document_service.get_document_by_id(mock_db, VALID_OBJECT_ID)


# --- list_documents ---

@pytest.mark.asyncio
async def test_list_documents_returns_list(document_service, mock_db, mock_collection):
    cursor = MagicMock()
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "filename": "archivo.pdf",
            "text": "Texto",
            "checksum": "abc123",
            "created_at": NOW,
            "updated_at": NOW,
        }
    ])
    mock_collection.find = MagicMock(return_value=cursor)

    result = await document_service.list_documents(mock_db)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].filename == "archivo.pdf"


@pytest.mark.asyncio
async def test_list_documents_returns_empty_list(document_service, mock_db):
    result = await document_service.list_documents(mock_db)
    assert result == []


# --- update_document ---

@pytest.mark.asyncio
async def test_update_document_returns_updated_response(document_service, mock_db, mock_collection):
    updated = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "filename": "nuevo.pdf",
        "text": "Texto",
        "checksum": "abc123",
        "created_at": NOW,
        "updated_at": NOW,
    }
    mock_collection.find_one = AsyncMock(side_effect=[
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "filename": "archivo.pdf",
            "text": "Texto",
            "checksum": "abc123",
            "created_at": NOW,
            "updated_at": NOW,
        },
        updated,
    ])

    result = await document_service.update_document(
        mock_db, VALID_OBJECT_ID, DocumentUpdate(filename="nuevo.pdf")
    )

    assert result.filename == "nuevo.pdf"


@pytest.mark.asyncio
async def test_update_document_raises_not_found(document_service, mock_db, mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await document_service.update_document(
            mock_db, VALID_OBJECT_ID, DocumentUpdate(filename="nuevo.pdf")
        )


@pytest.mark.asyncio
async def test_update_document_with_empty_payload_returns_current(document_service, mock_db, mock_collection):
    existing = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "filename": "archivo.pdf",
        "text": "Texto",
        "checksum": "abc123",
        "created_at": NOW,
        "updated_at": NOW,
    }
    mock_collection.find_one = AsyncMock(return_value=existing)

    result = await document_service.update_document(mock_db, VALID_OBJECT_ID, DocumentUpdate())

    assert result.filename == "archivo.pdf"
    mock_collection.update_one.assert_not_called()


# --- delete_document ---

@pytest.mark.asyncio
async def test_delete_document_succeeds(document_service, mock_db):
    result = await document_service.delete_document(mock_db, VALID_OBJECT_ID)
    assert result is None


@pytest.mark.asyncio
async def test_delete_document_raises_not_found(document_service, mock_db, mock_collection):
    mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))

    with pytest.raises(NotFoundException):
        await document_service.delete_document(mock_db, VALID_OBJECT_ID)
