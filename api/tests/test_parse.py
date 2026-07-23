import io
from unittest.mock import MagicMock

import docx
import fitz
import pytesseract
import pytest

from ingest.parse import extract_text


def test_extract_text_from_docx_with_real_text_layer():
    doc = docx.Document()
    doc.add_paragraph("Patient seen on 2024-01-15.")
    buf = io.BytesIO()
    doc.save(buf)

    result = extract_text(buf.getvalue(), "record.docx")

    assert result == [(None, "Patient seen on 2024-01-15.")]


def test_extract_text_from_pdf_with_real_text_layer():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Deposition transcript page one.")
    pdf_bytes = doc.tobytes()

    result = extract_text(pdf_bytes, "deposition.pdf")

    assert len(result) == 1
    page_number, text = result[0]
    assert page_number == 1
    assert "Deposition transcript page one." in text


def test_extract_text_falls_back_to_ocr_when_page_has_no_text_layer(monkeypatch):
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()

    fake_ocr = MagicMock(return_value="OCR fallback text")
    monkeypatch.setattr(pytesseract, "image_to_string", fake_ocr)

    result = extract_text(pdf_bytes, "scanned.pdf")

    assert result == [(1, "OCR fallback text")]
    fake_ocr.assert_called_once()


def test_extract_text_raises_for_unsupported_extension():
    with pytest.raises(ValueError):
        extract_text(b"", "notes.txt")
