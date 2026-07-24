import json
from unittest.mock import MagicMock

import pytest

from chronology import build


def _fake_db(documents_data, chunks_data, edited_entries=None):
    """Build a fake supabase client whose .table(name) routes to a per-table mock
    so that documents/chunks/chronology_entries chains don't collide."""
    tables = {
        "documents": MagicMock(),
        "chunks": MagicMock(),
        "chronology_entries": MagicMock(),
    }
    tables["documents"].select.return_value.eq.return_value.execute.return_value.data = documents_data
    tables["chunks"].select.return_value.in_.return_value.execute.return_value.data = chunks_data
    tables["chronology_entries"].select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
        edited_entries or []
    )

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
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = expected_rows

    result = build.build_chronology("case-1")

    prompt = captured_prompt["value"]
    earlier_idx = prompt.index("Initial meeting occurred on 2024-01-01")
    later_idx = prompt.index("Contract signed on 2024-01-15")
    assert earlier_idx < later_idx

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


def test_build_chronology_deletes_only_unedited_entries_before_inserting_fresh_ones(monkeypatch):
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
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Something happened.",
                    "source_document_id": "doc-1",
                    "source_location": 1,
                }
            ]
        ),
    )

    build.build_chronology("case-1")

    entries_table = db.__tables__["chronology_entries"]
    entries_table.delete.assert_called_once()
    entries_table.delete.return_value.eq.assert_any_call("case_id", "case-1")
    entries_table.delete.return_value.eq.return_value.eq.assert_called_once_with(
        "edited_by_attorney", False
    )
    entries_table.delete.return_value.eq.return_value.eq.return_value.execute.assert_called_once()
    entries_table.insert.assert_called_once()
    # delete must happen before insert, not after
    delete_call_index = [c[0] for c in entries_table.method_calls].index("delete")
    insert_call_index = [c[0] for c in entries_table.method_calls].index("insert")
    assert delete_call_index < insert_call_index


def test_build_chronology_does_not_duplicate_entry_already_covered_by_an_edited_entry(monkeypatch):
    """Regression test for a live bug: regenerating a case after an attorney
    edit created a second, stale entry for the same source excerpt alongside
    the correctly-preserved edited one, instead of skipping it."""
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "ER visit on 2024-01-03 for back pain.",
        },
        {
            "id": "chunk-2",
            "document_id": "doc-1",
            "page_number": 2,
            "content": "Follow-up visit on 2024-01-20.",
        },
    ]
    existing_edited_entry = {
        "id": "entry-1",
        "case_id": "case-1",
        "event_date": "2024-01-03",
        "summary": "MANUALLY CORRECTED: attorney-verified summary.",
        "source_document_id": "doc-1",
        "source_location": 1,
        "version": 2,
        "edited_by_attorney": True,
    }
    db = _fake_db(documents_data, chunks_data, edited_entries=[existing_edited_entry])
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-03",
                    "summary": "Stale AI-generated summary for the same visit.",
                    "source_document_id": "doc-1",
                    "source_location": 1,
                },
                {
                    "event_date": "2024-01-20",
                    "summary": "Follow-up visit summary.",
                    "source_document_id": "doc-1",
                    "source_location": 2,
                },
            ]
        ),
    )
    new_row = {
        "case_id": "case-1",
        "event_date": "2024-01-20",
        "summary": "Follow-up visit summary.",
        "source_document_id": "doc-1",
        "source_location": 2,
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [new_row]

    result = build.build_chronology("case-1")

    # only the non-overlapping fresh entry was inserted -- the duplicate for
    # (doc-1, page 1), already covered by the edited entry, was filtered out
    db.__tables__["chronology_entries"].insert.assert_called_once_with([new_row])
    assert result == [existing_edited_entry, new_row]
    assert not any(
        e["summary"] == "Stale AI-generated summary for the same visit." for e in result
    )


def test_build_chronology_does_not_filter_a_different_event_on_the_same_page(monkeypatch):
    """Regression test for a live bug: a single-page document describing
    THREE distinct visits (all source_location="1", since chunking is
    page-granular, not event-granular) had ONE visit edited by the
    attorney. Regeneration then treated the other two, genuinely different,
    never-edited events on that same page as duplicates and dropped them."""
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "ER visit on 2024-01-03. Follow-up on 2024-01-20. Follow-up on 2024-03-05.",
        }
    ]
    existing_edited_entry = {
        "id": "entry-1",
        "case_id": "case-1",
        "event_date": "2024-01-03",
        "summary": "MANUALLY CORRECTED: attorney-verified summary.",
        "source_document_id": "doc-1",
        "source_location": "1",
        "version": 2,
        "edited_by_attorney": True,
    }
    db = _fake_db(documents_data, chunks_data, edited_entries=[existing_edited_entry])
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-03",
                    "summary": "Stale AI-generated summary for the same visit.",
                    "source_document_id": "doc-1",
                    "source_location": "1",
                },
                {
                    "event_date": "2024-01-20",
                    "summary": "Follow-up visit summary.",
                    "source_document_id": "doc-1",
                    "source_location": "1",
                },
                {
                    "event_date": "2024-03-05",
                    "summary": "Second follow-up visit summary.",
                    "source_document_id": "doc-1",
                    "source_location": "1",
                },
            ]
        ),
    )
    inserted_rows = [
        {
            "case_id": "case-1",
            "event_date": "2024-01-20",
            "summary": "Follow-up visit summary.",
            "source_document_id": "doc-1",
            "source_location": "1",
        },
        {
            "case_id": "case-1",
            "event_date": "2024-03-05",
            "summary": "Second follow-up visit summary.",
            "source_document_id": "doc-1",
            "source_location": "1",
        },
    ]
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = inserted_rows

    result = build.build_chronology("case-1")

    # both never-edited events on the same page must survive regeneration --
    # only the one matching the edited entry's (doc, location, date) is dropped
    db.__tables__["chronology_entries"].insert.assert_called_once_with(inserted_rows)
    assert result == [existing_edited_entry, *inserted_rows]


def test_build_chronology_strips_markdown_fence_from_llm_response(monkeypatch):
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
    fenced_response = (
        "```json\n"
        + json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Something happened.",
                    "source_document_id": "doc-1",
                    "source_location": 1,
                }
            ]
        )
        + "\n```"
    )
    monkeypatch.setattr(build, "generate", lambda prompt: fenced_response)

    expected_row = {
        "case_id": "case-1",
        "event_date": "2024-01-01",
        "summary": "Something happened.",
        "source_document_id": "doc-1",
        "source_location": 1,
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [expected_row]

    result = build.build_chronology("case-1")

    assert result == [expected_row]


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
