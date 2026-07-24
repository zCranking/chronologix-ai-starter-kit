import json
from unittest.mock import MagicMock

import pytest

from flags import detect


def _fake_db(entries):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = entries
    return db


def test_detect_flags_happy_path_inserts_flags_from_llm_response(monkeypatch):
    entries = [
        {"id": "entry-1", "case_id": "case-1", "event_date": "2024-01-01", "summary": "Contract signed on Jan 1"},
        {"id": "entry-2", "case_id": "case-1", "event_date": "2024-01-05", "summary": "Contract signed on Jan 5"},
    ]
    db = _fake_db(entries)
    monkeypatch.setattr(detect, "get_client", lambda: db)

    llm_response = json.dumps(
        [
            {
                "description": "Conflicting contract signing dates between entry-1 and entry-2",
                "related_entry_ids": ["entry-1", "entry-2"],
            }
        ]
    )
    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["prompt"] = prompt
        return llm_response

    monkeypatch.setattr(detect, "generate", fake_generate)

    result = detect.detect_flags("case-1")

    assert "Contract signed on Jan 1" in captured_prompt["prompt"]
    assert "Contract signed on Jan 5" in captured_prompt["prompt"]

    db.table.return_value.insert.assert_called_once_with(
        [
            {
                "case_id": "case-1",
                "description": "Conflicting contract signing dates between entry-1 and entry-2",
                "related_entry_ids": ["entry-1", "entry-2"],
            }
        ]
    )
    assert result == [
        {
            "case_id": "case-1",
            "description": "Conflicting contract signing dates between entry-1 and entry-2",
            "related_entry_ids": ["entry-1", "entry-2"],
        }
    ]


def test_detect_flags_returns_empty_list_when_no_chronology_entries(monkeypatch):
    db = _fake_db([])
    monkeypatch.setattr(detect, "get_client", lambda: db)

    generate_mock = MagicMock()
    monkeypatch.setattr(detect, "generate", generate_mock)

    result = detect.detect_flags("case-1")

    assert result == []
    generate_mock.assert_not_called()
    db.table.return_value.insert.assert_not_called()


def test_detect_flags_returns_empty_list_when_llm_finds_no_inconsistencies(monkeypatch):
    entries = [
        {"id": "entry-1", "case_id": "case-1", "event_date": "2024-01-01", "summary": "Contract signed"},
    ]
    db = _fake_db(entries)
    monkeypatch.setattr(detect, "get_client", lambda: db)
    monkeypatch.setattr(detect, "generate", lambda prompt: "[]")

    result = detect.detect_flags("case-1")

    assert result == []
    db.table.return_value.insert.assert_not_called()


def test_detect_flags_strips_markdown_fence_from_llm_response(monkeypatch):
    entries = [
        {"id": "entry-1", "case_id": "case-1", "event_date": "2024-01-01", "summary": "Contract signed"},
    ]
    db = _fake_db(entries)
    monkeypatch.setattr(detect, "get_client", lambda: db)
    fenced_response = "```json\n" + json.dumps(
        [{"description": "conflict", "related_entry_ids": ["entry-1"]}]
    ) + "\n```"
    monkeypatch.setattr(detect, "generate", lambda prompt: fenced_response)

    result = detect.detect_flags("case-1")

    assert result == [
        {"case_id": "case-1", "description": "conflict", "related_entry_ids": ["entry-1"]}
    ]


def test_detect_flags_raises_on_malformed_llm_json(monkeypatch):
    entries = [
        {"id": "entry-1", "case_id": "case-1", "event_date": "2024-01-01", "summary": "Contract signed"},
    ]
    db = _fake_db(entries)
    monkeypatch.setattr(detect, "get_client", lambda: db)
    monkeypatch.setattr(detect, "generate", lambda prompt: "not valid json")

    with pytest.raises(json.JSONDecodeError):
        detect.detect_flags("case-1")
