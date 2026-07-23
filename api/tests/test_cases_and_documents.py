from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_create_case_returns_case_with_dev_firm_id(monkeypatch):
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "case-1", "name": "Smith v. Jones", "firm_id": main.DEV_FIRM_ID}
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.post("/cases", json={"name": "Smith v. Jones"})

    assert response.status_code == 200
    assert response.json()["firm_id"] == "00000000-0000-0000-0000-000000000001"


def test_upload_document_creates_pending_document_and_schedules_processing(monkeypatch):
    db = MagicMock()
    document_row = {
        "id": "doc-1",
        "case_id": "case-1",
        "status": "pending",
        "original_filename": "record.pdf",
    }
    db.table.return_value.insert.return_value.execute.return_value.data = [document_row]
    monkeypatch.setattr(main, "get_client", lambda: db)
    fake_process = MagicMock()
    monkeypatch.setattr(main, "process_document", fake_process)

    response = client.post(
        "/cases/case-1/documents",
        files={"file": ("record.pdf", b"file contents", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    db.storage.from_.return_value.upload.assert_called_once()
    fake_process.assert_called_once_with("doc-1")


def test_get_document_returns_404_when_not_found(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases/case-1/documents/doc-1")

    assert response.status_code == 404
