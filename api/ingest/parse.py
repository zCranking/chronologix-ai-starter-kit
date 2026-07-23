import io

import fitz
import pypdf
import pytesseract
from PIL import Image

from core.config import settings

if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text(file_bytes: bytes, filename: str) -> list[tuple[int | None, str]]:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return _extract_pdf(file_bytes)
    if ext == "docx":
        return _extract_docx(file_bytes)
    raise ValueError(f"unsupported file type: {ext}")


def _extract_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages: list[tuple[int, str]] = []
    doc = None
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            if doc is None:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
            pixmap = doc[i - 1].get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            text = pytesseract.image_to_string(image).strip()
        pages.append((i, text))
    return pages


def _extract_docx(file_bytes: bytes) -> list[tuple[None, str]]:
    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return [(None, text)]
