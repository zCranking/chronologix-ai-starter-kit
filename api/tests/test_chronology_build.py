import json
from unittest.mock import MagicMock

import pytest

from chronology import build


def _fake_db(documents_data, chunks_data):
    """Build a fake supabase client whose .table(name) routes to a per-table mock
    so that documents/chunks/chronology_entries chains don't collide."""
    tables = {
        "documents": MagicMock(),
        "chunks": MagicMock(),
        "chronology_entries": MagicMock(),
    }
    tables["documents"].select.return_value.eq.return_value.execute.return_value.data = documents_data
    tables["chunks"].select.return_value.in_.return_value.execute.return_value.data = chunks_data

    db = MagicMock()
    db.table.side_effect = lambda name: tables[name]
    db.__tables__ = tables  # convenience handle for assertions
    return db


def test_build_chronology_happy_path_sorts_by_date_and_inserts_entries(monkeypatch):
    documents_data = [{"id": "doc-1"}, {"id": "doc-2"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 3,
            "content": "Contract signed on 2024-01-15 by both parties.",
        },
        {
            "id": "chunk-2",
            "document_id": "doc-2",
            "page_number": 1,
            "content": "Initial meeting occurred on 2024-01-01 to discuss terms.",
        },
    ]
    db = _fake_db(documents_data, chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)

    llm_response = json.dumps(
        [
            {
                "event_date": "2024-01-01",
                "summary": "Initial meeting to discuss terms.",
                "source_document_id": "doc-2",
                "source_location": 1,
            },
            {
                "event_date": "2024-01-15",
                "summary": "Contract signed by both parties.",
                "source_document_id": "doc-1",
                "source_location": 3,
            },
        ]
    )
    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["value"] = prompt
        return llm_response

    monkeypatch.setattr(build, "generate", fake_generate)

    result = build.build_chronology("case-1")

    prompt = captured_prompt["value"]
    earlier_idx = prompt.index("Initial meeting occurred on 2024-01-01")
    later_idx = prompt.index("Contract signed on 2024-01-15")
    assert earlier_idx < later_idx

    expected_rows = [
        {
            "case_id": "case-1",
            "event_date": "2024-01-01",
            "summary": "Initial meeting to discuss terms.",
            "source_document_id": "doc-2",
            "source_location": 1,
        },
        {
            "case_id": "case-1",
            "event_date": "2024-01-15",
            "summary": "Contract signed by both parties.",
            "source_document_id": "doc-1",
            "source_location": 3,
        },
    ]
    assert result == expected_rows
    db.__tables__["chronology_entries"].insert.assert_called_once_with(expected_rows)
    db.__tables__["chronology_entries"].insert.return_value.execute.assert_called_once()


def test_build_chronology_returns_empty_list_when_case_has_no_documents(monkeypatch):
    db = _fake_db([], [])
    monkeypatch.setattr(build, "get_client", lambda: db)

    generate_mock = MagicMock()
    monkeypatch.setattr(build, "generate", generate_mock)

    result = build.build_chronology("case-1")

    assert result == []
    generate_mock.assert_not_called()
    db.__tables__["chronology_entries"].insert.assert_not_called()


def test_build_chronology_puts_undated_chunks_after_dated_chunks(monkeypatch):
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-undated",
            "document_id": "doc-1",
            "page_number": 5,
            "content": "General background with no date mentioned anywhere.",
        },
        {
            "id": "chunk-dated-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "Event happened on 2024-02-01 as noted.",
        },
        {
            "id": "chunk-dated-2",
            "document_id": "doc-1",
            "page_number": 2,
            "content": "Another event happened on 2024-03-01 as noted.",
        },
    ]
    db = _fake_db(documents_data, chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)

    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["value"] = prompt
        return json.dumps([])

    monkeypatch.setattr(build, "generate", fake_generate)

    build.build_chronology("case-1")

    prompt = captured_prompt["value"]
    dated_1_idx = prompt.index("Event happened on 2024-02-01")
    dated_2_idx = prompt.index("Another event happened on 2024-03-01")
    undated_idx = prompt.index("General background with no date mentioned anywhere.")
    assert dated_1_idx < undated_idx
    assert dated_2_idx < undated_idx


def test_build_chronology_raises_on_malformed_llm_json(monkeypatch):
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "Something happened on 2024-01-01.",
        }
    ]
    db = _fake_db(documents_data, chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(build, "generate", lambda prompt: "not valid json")

    with pytest.raises(json.JSONDecodeError):
        build.build_chronology("case-1")
