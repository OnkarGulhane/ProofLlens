"""Helper utilities for generating synthetic PDF documents for testing."""

import io
from typing import List
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject


def create_synthetic_pdf(pages_text: List[str]) -> bytes:
    """Generates a valid PDF with multiple pages containing the specified text."""
    writer = PdfWriter()

    for text in pages_text:
        page = writer.add_blank_page(width=400, height=400)
        
        # Escape parenthesis in PDF string syntax
        escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        text_stream = f"BT /F1 12 Tf 50 250 Td ({escaped_text}) Tj ET".encode("latin1")
        
        stream = DecodedStreamObject()
        stream.set_data(text_stream)
        page[NameObject("/Contents")] = stream

        font = DictionaryObject()
        font[NameObject("/Type")] = NameObject("/Font")
        font[NameObject("/Subtype")] = NameObject("/Type1")
        font[NameObject("/BaseFont")] = NameObject("/Helvetica")

        res = DictionaryObject()
        res[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
        page[NameObject("/Resources")] = res

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_blank_pdf(num_pages: int = 1) -> bytes:
    """Generates a PDF with blank pages (no text content) for testing scanned/empty heuristics."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
