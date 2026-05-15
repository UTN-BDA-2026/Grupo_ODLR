# tests/test_document_repo.py

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.models.document import DocumentCreateDocument, DocumentUpdateDocument
from app.repositories.document_repo import DocumentRepository

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"
NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)

SAMPLE_DOC = {
    "_id": ObjectId(VALID_OBJECT_ID),
    "filename": "archivo.pdf",
    "text": "Texto extraído del PDF",
    "checksum": "abc123def456",
    "created_at": NOW,
    "updated_at": NOW,
}


@pytest.fixture
def mock_collection():
    col = MagicMock()
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(VALID_OBJECT_ID)))
    col.find_one = AsyncMock(return_value=SAMPLE_DOC.copy())
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.count_documents = AsyncMock(return_value=2)
    cursor = MagicMock()
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[SAMPLE_DOC.copy()])
    col.find = MagicMock(return_value=cursor)
    return col


@pytest.fixture
def mock_db(mock_collection):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


@pytest.fixture
def repo(mock_db):
    return DocumentRepository(db=mock_db)


@pytest.fixture
def create_doc():
    return DocumentCreateDocument(
        filename="archivo.pdf",
        text="Texto extraído del PDF",
        checksum="abc123def456",
        created_at=NOW,
        updated_at=NOW,
    )


# --- create ---

@pytest.mark.asyncio
async def test_create_returns_document_document(repo, create_doc):
    result = await repo.create(create_doc)
    assert result.id == VALID_OBJECT_ID
    assert result.filename == "archivo.pdf"
    assert result.checksum == "abc123def456"


@pytest.mark.asyncio
async def test_create_persists_all_fields(repo, create_doc, mock_collection):
    await repo.create(create_doc)
    call_args = mock_collection.insert_one.call_args[0][0]
    assert call_args["filename"] == "archivo.pdf"
    assert call_args["checksum"] == "abc123def456"
    assert "created_at" in call_args


# --- get_by_id ---

@pytest.mark.asyncio
async def test_get_by_id_returns_document_document(repo):
    result = await repo.get_by_id(VALID_OBJECT_ID)
    assert result is not None
    assert result.id == VALID_OBJECT_ID
    assert result.filename == "archivo.pdf"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(repo, mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)
    result = await repo.get_by_id(VALID_OBJECT_ID)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_with_invalid_id_returns_none(repo):
    result = await repo.get_by_id("id-malformado")
    assert result is None


# --- get_all ---

@pytest.mark.asyncio
async def test_get_all_returns_list_of_documents(repo):
    result = await repo.get_all()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].filename == "archivo.pdf"


@pytest.mark.asyncio
async def test_get_all_empty_returns_empty_list(repo, mock_collection):
    cursor = MagicMock()
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=cursor)
    result = await repo.get_all()
    assert result == []


# --- update ---

@pytest.mark.asyncio
async def test_update_returns_updated_document(repo, mock_collection):
    updated_doc = SAMPLE_DOC.copy()
    updated_doc["filename"] = "nuevo.pdf"
    mock_collection.find_one = AsyncMock(return_value=updated_doc)
    obj_in = DocumentUpdateDocument(filename="nuevo.pdf", updated_at=NOW)
    result = await repo.update(VALID_OBJECT_ID, obj_in)
    assert result is not None
    assert result.filename == "nuevo.pdf"


@pytest.mark.asyncio
async def test_update_with_invalid_id_returns_none(repo):
    obj_in = DocumentUpdateDocument(filename="nuevo.pdf")
    result = await repo.update("id-invalido", obj_in)
    assert result is None


# --- delete ---

@pytest.mark.asyncio
async def test_delete_returns_true_when_found(repo):
    result = await repo.delete(VALID_OBJECT_ID)
    assert result is True


@pytest.mark.asyncio
async def test_delete_returns_false_when_not_found(repo, mock_collection):
    mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    result = await repo.delete(VALID_OBJECT_ID)
    assert result is False


@pytest.mark.asyncio
async def test_delete_with_invalid_id_returns_false(repo):
    result = await repo.delete("id-invalido")
    assert result is False


# --- exists ---

@pytest.mark.asyncio
async def test_exists_returns_true_when_found(repo):
    result = await repo.exists("checksum", "abc123def456")
    assert result is True


@pytest.mark.asyncio
async def test_exists_returns_false_when_not_found(repo, mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)
    result = await repo.exists("checksum", "inexistente")
    assert result is False


# --- count ---

@pytest.mark.asyncio
async def test_count_returns_integer(repo):
    result = await repo.count()
    assert result == 2


@pytest.mark.asyncio
async def test_count_with_filters(repo, mock_collection):
    mock_collection.count_documents = AsyncMock(return_value=1)
    result = await repo.count({"filename": "archivo.pdf"})
    assert result == 1


# --- find_by_checksum ---

@pytest.mark.asyncio
async def test_find_by_checksum_returns_document_when_exists(repo):
    result = await repo.find_by_checksum("abc123def456")
    assert result is not None
    assert result.checksum == "abc123def456"


@pytest.mark.asyncio
async def test_find_by_checksum_returns_none_when_not_exists(repo, mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)
    result = await repo.find_by_checksum("checksum-inexistente")
    assert result is None
