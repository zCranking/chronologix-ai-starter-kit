from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_generate_demand_letter_returns_draft(monkeypatch):
    row = {"id": "dl-1", "case_id": "case-1", "body": "DRAFT...", "version": 1, "edited_by_attorney": False}
    monkeypatch.setattr(main, "draft_demand_letter", lambda case_id: row)
    response = client.post("/cases/case-1/demand-letter")
    assert response.status_code == 200
    assert response.json()["version"] == 1


def test_generate_demand_letter_returns_400_on_guard_failure(monkeypatch):
    def raise_guard(case_id):
        raise ValueError("a demand letter can only be drafted from a signed-off chronology")
    monkeypatch.setattr(main, "draft_demand_letter", raise_guard)
    response = client.post("/cases/case-1/demand-letter")
    assert response.status_code == 400
    assert "signed-off" in response.json()["detail"]


def test_list_demand_letters_returns_versions(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "dl-2", "case_id": "case-1", "body": "v2", "version": 2, "edited_by_attorney": True},
        {"id": "dl-1", "case_id": "case-1", "body": "v1", "version": 1, "edited_by_attorney": False},
    ]
    monkeypatch.setattr(main, "get_client", lambda: db)
    response = client.get("/cases/case-1/demand-letters")
    assert response.status_code == 200
    assert [r["version"] for r in response.json()] == [2, 1]


def test_update_demand_letter_bumps_version_and_marks_edited(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "id": "dl-1", "case_id": "case-1", "body": "old", "version": 1, "edited_by_attorney": False
    }
    updated = {"id": "dl-1", "case_id": "case-1", "body": "new body", "version": 2, "edited_by_attorney": True}
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    monkeypatch.setattr(main, "get_client", lambda: db)
    response = client.patch("/cases/case-1/demand-letters/dl-1", json={"body": "new body"})
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["edited_by_attorney"] is True
    db.table.return_value.update.assert_called_once_with(
        {"body": "new body", "version": 2, "edited_by_attorney": True}
    )


def test_update_demand_letter_returns_404_when_not_found(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    monkeypatch.setattr(main, "get_client", lambda: db)
    response = client.patch("/cases/case-1/demand-letters/missing", json={"body": "x"})
    assert response.status_code == 404
