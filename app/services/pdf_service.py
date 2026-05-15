"""PDF text extraction service.

Follows Clean Code principles.
SRP: Only handles PDF text extraction.
"""

import fitz  # PyMuPDF
import hashlib

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes.

    Args:
        pdf_bytes: PDF content as bytes.

    Returns:
        Extracted text.

    Raises:
        ValueError: If bytes are not a valid PDF.
    """
    logger.debug("Extracting text from PDF", extra={"pdf_size": len(pdf_bytes)})

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(
            "Invalid PDF bytes",
            extra={"pdf_size": len(pdf_bytes), "error": str(e)},
        )
        raise ValueError("Invalid PDF bytes provided") from e

    text_parts = []
    for page_num, page in enumerate(doc, 1):
        page_text = page.get_text()
        text_parts.append(page_text)
        logger.debug(
            "Extracted text from page",
            extra={"page": page_num, "text_length": len(page_text)},
        )

    doc.close()

    full_text = "".join(text_parts)
    logger.info(
        "PDF text extraction completed",
        extra={
            "pages": len(text_parts),
            "total_length": len(full_text),
        },
    )

    return full_text


def calculate_checksum(file_bytes: bytes) -> str:
    """
    Calcula el checksum SHA-256 de un archivo.

    Args:
        file_bytes: contenido del archivo en bytes

    Returns:
        String hexadecimal de 64 caracteres (SHA-256)
    """
    return hashlib.sha256(file_bytes).hexdigest()