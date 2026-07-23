from unittest.mock import MagicMock

import pytest

from ingest import pipeline


def _fake_db(doc_row):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = doc_row
    db.storage.from_.return_value.download.return_value = b"file bytes"
    return db


def test_process_document_happy_path_inserts_chunks_and_marks_processed(monkeypatch):
    doc_row = {"id": "doc-1", "storage_path": "case-1/doc.pdf", "original_filename": "doc.pdf"}
    db = _fake_db(doc_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(pipeline, "extract_text", lambda file_bytes, filename: [(1, "page text")])
    monkeypatch.setattr(pipeline, "chunk_text", lambda pages: [(1, "chunk one"), (1, "chunk two")])
    monkeypatch.setattr(pipeline, "embed", lambda texts: [[0.1, 0.2], [0.3, 0.4]])

    pipeline.process_document("doc-1")

    db.table.return_value.insert.assert_called_once_with(
        [
            {"document_id": "doc-1", "page_number": 1, "content": "chunk one", "embedding": [0.1, 0.2]},
            {"document_id": "doc-1", "page_number": 1, "content": "chunk two", "embedding": [0.3, 0.4]},
        ]
    )
    db.table.return_value.update.assert_called_once_with({"status": "processed"})


def test_process_document_marks_failed_and_reraises_on_extraction_error(monkeypatch):
    doc_row = {"id": "doc-1", "storage_path": "case-1/doc.pdf", "original_filename": "doc.pdf"}
    db = _fake_db(doc_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)

    def raise_extract(file_bytes, filename):
        raise ValueError("bad file")

    monkeypatch.setattr(pipeline, "extract_text", raise_extract)

    with pytest.raises(ValueError):
        pipeline.process_document("doc-1")

    db.table.return_value.update.assert_called_once_with({"status": "failed"})


def test_process_document_skips_chunk_insert_when_no_chunks(monkeypatch):
    doc_row = {"id": "doc-1", "storage_path": "case-1/doc.pdf", "original_filename": "doc.pdf"}
    db = _fake_db(doc_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(pipeline, "extract_text", lambda file_bytes, filename: [(1, "")])
    monkeypatch.setattr(pipeline, "chunk_text", lambda pages: [])
    monkeypatch.setattr(pipeline, "embed", lambda texts: [])

    pipeline.process_document("doc-1")

    db.table.return_value.insert.assert_not_called()
    db.table.return_value.update.assert_called_once_with({"status": "processed"})
