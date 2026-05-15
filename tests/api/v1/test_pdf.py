"""
Tests for PDF endpoints.

Follows the Arrange-Act-Assert pattern.
Uses FastAPI TestClient for integration testing.
"""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConflictException, NotFoundException
from app.main import create_application
from app.schemas.document import DocumentResponse

VALID_ID = "507f1f77bcf86cd799439011"
NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def sample_response() -> DocumentResponse:
    return DocumentResponse(
        id=VALID_ID,
        filename="test_document.pdf",
        text="Hola mundo desde el PDF de prueba",
        checksum="abc123sha256",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.upload_pdf = AsyncMock()
    svc.get_document_by_id = AsyncMock()
    svc.list_documents = AsyncMock(return_value=[])
    svc.update_document = AsyncMock()
    svc.delete_document = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def client(mock_service):
    app = create_application()
    import app.api.v1.endpoints.pdf as pdf_module
    pdf_module.document_service = mock_service
    return TestClient(app)


# --- POST /upload ---

class TestPdfUploadEndpoint:
    """Test suite for POST /pdf/upload endpoint."""

    def test_upload_pdf_success(self, client, mock_service, sample_response, sample_pdf_bytes):
        mock_service.upload_pdf = AsyncMock(return_value=sample_response)

        pdf_file = BytesIO(sample_pdf_bytes)
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("test_document.pdf", pdf_file, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == VALID_ID
        assert data["filename"] == "test_document.pdf"
        assert "text" in data

    def test_upload_rejects_non_pdf_files(self, client):
        txt_file = BytesIO(b"This is not a PDF")
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("document.txt", txt_file, "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_rejects_file_exceeding_size_limit(self, client):
        oversized_content = b"%PDF-1.4" + b"x" * (51 * 1024 * 1024)
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("large.pdf", BytesIO(oversized_content), "application/pdf")},
        )
        assert response.status_code == 413

    def test_upload_rejects_invalid_pdf_content(self, client, mock_service):
        mock_service.upload_pdf = AsyncMock(side_effect=ValueError("Invalid PDF"))
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("fake.pdf", BytesIO(b"not a pdf"), "application/pdf")},
        )
        assert response.status_code == 400

    def test_upload_rejects_duplicate_pdf(self, client, mock_service, sample_pdf_bytes):
        mock_service.upload_pdf = AsyncMock(
            side_effect=ConflictException(f"El documento ya existe con id: {VALID_ID}")
        )
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("duplicado.pdf", BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 409

    def test_upload_requires_file(self, client):
        response = client.post("/api/v1/pdf/upload")
        assert response.status_code == 422

    def test_upload_accepts_unique_pdf(self, client, mock_service, sample_response, sample_pdf_bytes):
        mock_service.upload_pdf = AsyncMock(return_value=sample_response)
        response = client.post(
            "/api/v1/pdf/upload",
            files={"file": ("unico.pdf", BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200


# --- GET / ---

class TestListDocumentsEndpoint:

    def test_list_documents_returns_200_with_list(self, client, mock_service, sample_response):
        mock_service.list_documents = AsyncMock(return_value=[sample_response])

        response = client.get("/api/v1/pdf/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == VALID_ID

    def test_list_documents_returns_empty_list(self, client, mock_service):
        mock_service.list_documents = AsyncMock(return_value=[])

        response = client.get("/api/v1/pdf/")

        assert response.status_code == 200
        assert response.json() == []


# --- GET /{document_id} ---

class TestGetDocumentEndpoint:

    def test_get_document_success(self, client, mock_service, sample_response):
        mock_service.get_document_by_id = AsyncMock(return_value=sample_response)

        response = client.get(f"/api/v1/pdf/{VALID_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == VALID_ID
        assert data["filename"] == "test_document.pdf"

    def test_get_document_not_found(self, client, mock_service):
        mock_service.get_document_by_id = AsyncMock(
            side_effect=NotFoundException("Document not found")
        )

        response = client.get(f"/api/v1/pdf/{VALID_ID}")

        assert response.status_code == 404
        assert "detail" in response.json()


# --- PUT /{document_id} ---

class TestUpdateDocumentEndpoint:

    def test_update_document_success(self, client, mock_service, sample_response):
        updated = sample_response.model_copy(update={"filename": "nuevo.pdf"})
        mock_service.update_document = AsyncMock(return_value=updated)

        response = client.put(
            f"/api/v1/pdf/{VALID_ID}",
            json={"filename": "nuevo.pdf"},
        )

        assert response.status_code == 200
        assert response.json()["filename"] == "nuevo.pdf"

    def test_update_document_not_found(self, client, mock_service):
        mock_service.update_document = AsyncMock(
            side_effect=NotFoundException("Document not found")
        )

        response = client.put(
            f"/api/v1/pdf/{VALID_ID}",
            json={"filename": "nuevo.pdf"},
        )

        assert response.status_code == 404


# --- DELETE /{document_id} ---

class TestDeleteDocumentEndpoint:

    def test_delete_document_success(self, client, mock_service):
        mock_service.delete_document = AsyncMock(return_value=None)

        response = client.delete(f"/api/v1/pdf/{VALID_ID}")

        assert response.status_code == 204

    def test_delete_document_not_found(self, client, mock_service):
        mock_service.delete_document = AsyncMock(
            side_effect=NotFoundException("Document not found")
        )

        response = client.delete(f"/api/v1/pdf/{VALID_ID}")

        assert response.status_code == 404
