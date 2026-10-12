"""Unit tests for PDF extraction and validation."""

import pytest
from app.services.document_service import DocumentService
from app.core.exceptions import DocumentValidationError
from tests.pdf_helpers import create_synthetic_pdf, create_blank_pdf


def test_pdf_extraction_page_provenance():
    """Verify that multi-page PDFs preserve page count and 1-indexed physical page numbers."""
    page_1_text = "Page 1: ProofLens AI delivers evidence-grounded document analysis and verification."
    page_2_text = "Page 2: Provenance is preserved so every claim anchors back to an exact physical page."
    page_3_text = "Page 3: Hallucinations are mitigated through rigorous server-side cross-referencing."

    pdf_bytes = create_synthetic_pdf([page_1_text, page_2_text, page_3_text])

    total_pages, extracted = DocumentService.extract_pages_from_pdf(pdf_bytes, "report.pdf")

    assert total_pages == 3
    assert len(extracted) == 3

    # Check 1-indexed page numbers and extracted text
    assert extracted[0][0] == 1
    assert page_1_text in extracted[0][1]

    assert extracted[1][0] == 2
    assert page_2_text in extracted[1][1]

    assert extracted[2][0] == 3
    assert page_3_text in extracted[2][1]


def test_scanned_pdf_rejection_heuristic():
    """Verify that blank or scanned PDFs lacking digital text are rejected."""
    blank_pdf = create_blank_pdf(num_pages=2)

    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentService.extract_pages_from_pdf(blank_pdf, "scanned_invoice.pdf")

    assert "scanned image" in exc_info.value.message.lower()


def test_invalid_magic_bytes_rejection():
    """Verify that non-PDF files are rejected based on magic byte validation."""
    non_pdf = b"Plain text file content masquerading as a PDF."

    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentService.validate_pdf_content(non_pdf, "fake.pdf")

    assert "invalid magic bytes" in exc_info.value.message.lower()


def test_empty_content_rejection():
    """Verify that 0-byte uploads are rejected."""
    empty_bytes = b""

    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentService.validate_pdf_content(empty_bytes, "empty.pdf")

    assert "is empty" in exc_info.value.message.lower()
