from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_list_cases_returns_all_cases(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "case-1", "name": "Smith v. Jones", "firm_id": main.DEV_FIRM_ID, "case_type": "personal_injury"}
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "case-1", "name": "Smith v. Jones", "firm_id": main.DEV_FIRM_ID, "case_type": "personal_injury"}
    ]


def test_get_case_returns_case_detail(monkeypatch):
    db = MagicMock()
    case_row = {
        "id": "case-1",
        "name": "Smith v. Jones",
        "firm_id": main.DEV_FIRM_ID,
        "case_type": "personal_injury",
        "chronology_signed_off": False,
        "chronology_signed_off_at": None,
    }
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = (
        case_row
    )
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases/case-1")

    assert response.status_code == 200
    assert response.json() == case_row


def test_get_case_returns_404_when_not_found(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases/missing-case")

    assert response.status_code == 404


def test_list_documents_returns_documents_for_case(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "doc-1", "case_id": "case-1", "status": "processed", "original_filename": "record.pdf"}
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.get("/cases/case-1/documents")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "doc-1"


def test_list_chronology_returns_existing_entries_without_regenerating(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "entry-1", "case_id": "case-1", "event_date": "2024-01-15", "summary": "x"}
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)
    fake_build = MagicMock()
    monkeypatch.setattr(main, "build_chronology", fake_build)

    response = client.get("/cases/case-1/chronology")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "entry-1"
    fake_build.assert_not_called()


def test_list_flags_returns_existing_flags_without_regenerating(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "flag-1", "case_id": "case-1", "description": "conflicting dates"}
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)
    fake_detect = MagicMock()
    monkeypatch.setattr(main, "detect_flags", fake_detect)

    response = client.get("/cases/case-1/flags")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "flag-1"
    fake_detect.assert_not_called()


def test_update_chronology_entry_marks_edited_and_bumps_version(monkeypatch):
    db = MagicMock()
    existing = {"id": "entry-1", "case_id": "case-1", "version": 1}
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = (
        existing
    )
    updated = {**existing, "summary": "corrected summary", "version": 2, "edited_by_attorney": True}
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.patch(
        "/cases/case-1/chronology/entry-1", json={"summary": "corrected summary"}
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["edited_by_attorney"] is True
    db.table.return_value.update.assert_called_once_with(
        {"summary": "corrected summary", "version": 2, "edited_by_attorney": True}
    )


def test_update_chronology_entry_returns_404_when_not_found(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.patch(
        "/cases/case-1/chronology/missing-entry", json={"summary": "x"}
    )

    assert response.status_code == 404


def test_sign_off_case_sets_signed_off_true(monkeypatch):
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "case-1",
            "name": "Smith v. Jones",
            "firm_id": main.DEV_FIRM_ID,
            "case_type": "personal_injury",
            "chronology_signed_off": True,
            "chronology_signed_off_at": "2026-07-23T00:00:00+00:00",
        }
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)

    response = client.post("/cases/case-1/sign-off")

    assert response.status_code == 200
    assert response.json()["chronology_signed_off"] is True
    args, _ = db.table.return_value.update.call_args
    assert args[0]["chronology_signed_off"] is True
    assert "chronology_signed_off_at" in args[0]
