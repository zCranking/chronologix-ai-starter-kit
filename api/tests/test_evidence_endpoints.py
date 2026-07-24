from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_upload_evidence_infers_video_media_type_and_schedules_processing(monkeypatch):
    db = MagicMock()
    evidence_row = {
        "id": "ev-1",
        "case_id": "case-1",
        "status": "pending",
        "original_filename": "deposition.mp4",
        "media_type": "video",
        "confirmed_by_attorney": False,
    }
    db.table.return_value.insert.return_value.execute.return_value.data = [evidence_row]
    monkeypatch.setattr(main, "get_client", lambda: db)
    fake_process = MagicMock()
    monkeypatch.setattr(main, "process_evidence", fake_process)

    response = client.post(
        "/cases/case-1/evidence",
        files={"file": ("deposition.mp4", b"fake video bytes", "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["media_type"] == "video"
    assert body["status"] == "pending"
    db.storage.from_.assert_called_once_with("evidence")
    db.storage.from_.return_value.upload.assert_called_once()
    fake_process.assert_called_once_with("ev-1")


def test_upload_evidence_infers_audio_media_type(monkeypatch):
    db = MagicMock()
    evidence_row = {
        "id": "ev-2",
        "case_id": "case-1",
        "status": "pending",
        "original_filename": "interview.mp3",
        "media_type": "audio",
        "confirmed_by_attorney": False,
    }
    db.table.return_value.insert.return_value.execute.return_value.data = [evidence_row]
    monkeypatch.setattr(main, "get_client", lambda: db)
    monkeypatch.setattr(main, "process_evidence", MagicMock())

    response = client.post(
        "/cases/case-1/evidence",
        files={"file": ("interview.mp3", b"fake audio bytes", "audio/mpeg")},
    )

    assert response.status_code == 200
    assert response.json()["media_type"] == "audio"


def test_upload_evidence_rejects_unsupported_file_type(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(main, "get_client", lambda: db)
    monkeypatch.setattr(main, "process_evidence", MagicMock())

    response = client.post(
        "/cases/case-1/evidence",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    db.table.return_value.insert.assert_not_called()


def test_list_evidence_returns_evidence_for_case(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "ev-1",
            "case_id": "case-1",
            "status": "transcribed",
            "original_filename": "deposition.mp4",
            "media_type": "video",
            "confirmed_by_attorney": False,
        }
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases/case-1/evidence")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "ev-1"


def test_confirm_evidence_sets_confirmed_by_attorney_true(monkeypatch):
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "ev-1",
            "case_id": "case-1",
            "status": "transcribed",
            "original_filename": "deposition.mp4",
            "media_type": "video",
            "confirmed_by_attorney": True,
        }
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.post("/cases/case-1/evidence/ev-1/confirm")

    assert response.status_code == 200
    assert response.json()["confirmed_by_attorney"] is True
    db.table.return_value.update.assert_called_once_with({"confirmed_by_attorney": True})


def test_confirm_evidence_returns_404_when_not_found(monkeypatch):
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.post("/cases/case-1/evidence/missing/confirm")

    assert response.status_code == 404
