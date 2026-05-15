import pytest
import hashlib
from app.services.pdf_service import extract_text_from_bytes

def test_extract_text_returns_string(sample_pdf_bytes):
    result = extract_text_from_bytes(sample_pdf_bytes)
    assert isinstance(result, str)

def test_extract_text_returns_content(sample_pdf_bytes):
    result = extract_text_from_bytes(sample_pdf_bytes)
    assert len(result) > 0

def test_extract_text_with_invalid_bytes_raises_error():
    with pytest.raises(ValueError):
        extract_text_from_bytes(b"esto no es un pdf")

def test_calculate_checksum_returns_string(sample_pdf_bytes):
    from app.services.pdf_service import calculate_checksum
    result = calculate_checksum(sample_pdf_bytes)
    assert isinstance(result, str)

def test_calculate_checksum_is_sha256(sample_pdf_bytes):
    from app.services.pdf_service import calculate_checksum
    result = calculate_checksum(sample_pdf_bytes)
    # SHA-256 siempre produce exactamente 64 caracteres hex
    assert len(result) == 64

def test_calculate_checksum_is_deterministic(sample_pdf_bytes):
    from app.services.pdf_service import calculate_checksum
    # El mismo archivo siempre produce el mismo checksum
    result1 = calculate_checksum(sample_pdf_bytes)
    result2 = calculate_checksum(sample_pdf_bytes)
    assert result1 == result2

def test_calculate_checksum_differs_for_different_content():
    from app.services.pdf_service import calculate_checksum
    # Archivos distintos producen checksums distintos
    assert calculate_checksum(b"contenido A") != calculate_checksum(b"contenido B")