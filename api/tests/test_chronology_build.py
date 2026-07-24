import json
from unittest.mock import MagicMock

import pytest

from chronology import build


def _fake_db(
    documents_data=None,
    chunks_data=None,
    edited_entries=None,
    evidence_data=None,
    evidence_segments_data=None,
):
    """Build a fake supabase client whose .table(name) routes to a per-table mock
    so that documents/chunks/evidence/evidence_segments/chronology_entries
    chains don't collide."""
    tables = {
        "documents": MagicMock(),
        "chunks": MagicMock(),
        "evidence": MagicMock(),
        "evidence_segments": MagicMock(),
        "chronology_entries": MagicMock(),
    }
    tables["documents"].select.return_value.eq.return_value.execute.return_value.data = (
        documents_data or []
    )
    tables["chunks"].select.return_value.in_.return_value.execute.return_value.data = (
        chunks_data or []
    )
    tables[
        "evidence"
    ].select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
        evidence_data or []
    )
    tables["evidence_segments"].select.return_value.in_.return_value.execute.return_value.data = (
        evidence_segments_data or []
    )
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
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)

    llm_response = json.dumps(
        [
            {
                "event_date": "2024-01-01",
                "summary": "Initial meeting to discuss terms.",
                "source_type": "document",
                "source_id": "doc-2",
                "source_location": 1,
            },
            {
                "event_date": "2024-01-15",
                "summary": "Contract signed by both parties.",
                "source_type": "document",
                "source_id": "doc-1",
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
            "source_location": 1,
            "source_document_id": "doc-2",
        },
        {
            "case_id": "case-1",
            "event_date": "2024-01-15",
            "summary": "Contract signed by both parties.",
            "source_location": 3,
            "source_document_id": "doc-1",
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


def test_build_chronology_returns_empty_list_when_case_has_no_documents_or_evidence(monkeypatch):
    db = _fake_db()
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
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
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
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Something happened.",
                    "source_type": "document",
                    "source_id": "doc-1",
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
    delete_call_index = [c[0] for c in entries_table.method_calls].index("delete")
    insert_call_index = [c[0] for c in entries_table.method_calls].index("insert")
    assert delete_call_index < insert_call_index


def test_build_chronology_does_not_duplicate_entry_already_covered_by_an_edited_entry(monkeypatch):
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
        "source_evidence_id": None,
        "source_location": 1,
        "version": 2,
        "edited_by_attorney": True,
    }
    db = _fake_db(
        documents_data=documents_data, chunks_data=chunks_data, edited_entries=[existing_edited_entry]
    )
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-03",
                    "summary": "Stale AI-generated summary for the same visit.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": 1,
                },
                {
                    "event_date": "2024-01-20",
                    "summary": "Follow-up visit summary.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": 2,
                },
            ]
        ),
    )
    new_row = {
        "case_id": "case-1",
        "event_date": "2024-01-20",
        "summary": "Follow-up visit summary.",
        "source_location": 2,
        "source_document_id": "doc-1",
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [new_row]

    result = build.build_chronology("case-1")

    db.__tables__["chronology_entries"].insert.assert_called_once_with([new_row])
    assert result == [existing_edited_entry, new_row]
    assert not any(
        e["summary"] == "Stale AI-generated summary for the same visit." for e in result
    )


def test_build_chronology_does_not_filter_a_different_event_on_the_same_page(monkeypatch):
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
        "source_evidence_id": None,
        "source_location": "1",
        "version": 2,
        "edited_by_attorney": True,
    }
    db = _fake_db(
        documents_data=documents_data, chunks_data=chunks_data, edited_entries=[existing_edited_entry]
    )
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-03",
                    "summary": "Stale AI-generated summary for the same visit.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": "1",
                },
                {
                    "event_date": "2024-01-20",
                    "summary": "Follow-up visit summary.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": "1",
                },
                {
                    "event_date": "2024-03-05",
                    "summary": "Second follow-up visit summary.",
                    "source_type": "document",
                    "source_id": "doc-1",
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
            "source_location": "1",
            "source_document_id": "doc-1",
        },
        {
            "case_id": "case-1",
            "event_date": "2024-03-05",
            "summary": "Second follow-up visit summary.",
            "source_location": "1",
            "source_document_id": "doc-1",
        },
    ]
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = inserted_rows

    result = build.build_chronology("case-1")

    db.__tables__["chronology_entries"].insert.assert_called_once_with(inserted_rows)
    assert result == [existing_edited_entry, *inserted_rows]


def test_build_chronology_returns_combined_entries_sorted_by_event_date(monkeypatch):
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "Early event on 2024-01-01.",
        },
        {
            "id": "chunk-2",
            "document_id": "doc-1",
            "page_number": 2,
            "content": "Later event on 2024-06-01.",
        },
    ]
    later_edited_entry = {
        "id": "entry-1",
        "case_id": "case-1",
        "event_date": "2024-06-01",
        "summary": "MANUALLY CORRECTED: later event.",
        "source_document_id": "doc-1",
        "source_evidence_id": None,
        "source_location": 2,
        "version": 2,
        "edited_by_attorney": True,
    }
    db = _fake_db(
        documents_data=documents_data, chunks_data=chunks_data, edited_entries=[later_edited_entry]
    )
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Early event summary.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": 1,
                },
                {
                    "event_date": "2024-06-01",
                    "summary": "Stale later event summary.",
                    "source_type": "document",
                    "source_id": "doc-1",
                    "source_location": 2,
                },
            ]
        ),
    )
    earlier_new_row = {
        "case_id": "case-1",
        "event_date": "2024-01-01",
        "summary": "Early event summary.",
        "source_location": 1,
        "source_document_id": "doc-1",
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [earlier_new_row]

    result = build.build_chronology("case-1")

    assert [entry["event_date"] for entry in result] == ["2024-01-01", "2024-06-01"]


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
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)
    fenced_response = (
        "```json\n"
        + json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Something happened.",
                    "source_type": "document",
                    "source_id": "doc-1",
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
        "source_location": 1,
        "source_document_id": "doc-1",
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [expected_row]

    result = build.build_chronology("case-1")

    assert result == [expected_row]


def test_build_chronology_raises_on_invalid_source_type(monkeypatch):
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "Something happened on 2024-01-01.",
        }
    ]
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(
        build,
        "generate",
        lambda prompt: json.dumps(
            [
                {
                    "event_date": "2024-01-01",
                    "summary": "Something happened.",
                    "source_type": "documnet",  # typo -- must not silently misroute to source_document_id
                    "source_id": "doc-1",
                    "source_location": 1,
                }
            ]
        ),
    )

    with pytest.raises(ValueError, match="documnet"):
        build.build_chronology("case-1")


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
    db = _fake_db(documents_data=documents_data, chunks_data=chunks_data)
    monkeypatch.setattr(build, "get_client", lambda: db)
    monkeypatch.setattr(build, "generate", lambda prompt: "not valid json")

    with pytest.raises(json.JSONDecodeError):
        build.build_chronology("case-1")


def test_build_chronology_includes_confirmed_evidence_segments(monkeypatch):
    evidence_data = [{"id": "ev-1"}]
    evidence_segments_data = [
        {
            "id": "seg-1",
            "evidence_id": "ev-1",
            "start_time_seconds": 270,
            "end_time_seconds": 275,
            "speaker_label": "Speaker 1",
            "content": "Witness testified the incident occurred on 2024-04-10.",
        }
    ]
    db = _fake_db(evidence_data=evidence_data, evidence_segments_data=evidence_segments_data)
    monkeypatch.setattr(build, "get_client", lambda: db)

    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["value"] = prompt
        return json.dumps(
            [
                {
                    "event_date": "2024-04-10",
                    "summary": "Witness testified about the incident.",
                    "source_type": "evidence",
                    "source_id": "ev-1",
                    "source_location": "00:04:30",
                }
            ]
        )

    monkeypatch.setattr(build, "generate", fake_generate)

    expected_row = {
        "case_id": "case-1",
        "event_date": "2024-04-10",
        "summary": "Witness testified about the incident.",
        "source_location": "00:04:30",
        "source_evidence_id": "ev-1",
    }
    db.__tables__["chronology_entries"].insert.return_value.execute.return_value.data = [expected_row]

    result = build.build_chronology("case-1")

    prompt = captured_prompt["value"]
    assert "source_type=evidence" in prompt
    assert "location=00:04:30" in prompt
    assert "speaker=Speaker 1" in prompt
    assert "Witness testified the incident occurred on 2024-04-10." in prompt
    assert result == [expected_row]
    db.__tables__["chronology_entries"].insert.assert_called_once_with([expected_row])


def test_build_chronology_excludes_unconfirmed_evidence(monkeypatch):
    db = _fake_db()  # _fake_db's evidence mock, filtered by confirmed_by_attorney=True, returns []
    monkeypatch.setattr(build, "get_client", lambda: db)

    generate_mock = MagicMock()
    monkeypatch.setattr(build, "generate", generate_mock)

    result = build.build_chronology("case-1")

    assert result == []
    generate_mock.assert_not_called()
    # confirms the evidence fetch was actually scoped by confirmed_by_attorney=True
    db.__tables__["evidence"].select.return_value.eq.return_value.eq.assert_called_once_with(
        "confirmed_by_attorney", True
    )


def test_build_chronology_combines_documents_and_evidence_sorted_together(monkeypatch):
    documents_data = [{"id": "doc-1"}]
    chunks_data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "page_number": 1,
            "content": "Medical visit on 2024-01-01.",
        }
    ]
    evidence_data = [{"id": "ev-1"}]
    evidence_segments_data = [
        {
            "id": "seg-1",
            "evidence_id": "ev-1",
            "start_time_seconds": 30,
            "end_time_seconds": 35,
            "speaker_label": None,
            "content": "Deposition testimony about an event on 2024-02-01.",
        }
    ]
    db = _fake_db(
        documents_data=documents_data,
        chunks_data=chunks_data,
        evidence_data=evidence_data,
        evidence_segments_data=evidence_segments_data,
    )
    monkeypatch.setattr(build, "get_client", lambda: db)

    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["value"] = prompt
        return json.dumps([])

    monkeypatch.setattr(build, "generate", fake_generate)

    build.build_chronology("case-1")

    prompt = captured_prompt["value"]
    doc_idx = prompt.index("Medical visit on 2024-01-01")
    evidence_idx = prompt.index("Deposition testimony about an event on 2024-02-01")
    assert doc_idx < evidence_idx  # earlier date (document) comes before later date (evidence)


def test_format_excerpts_omits_speaker_tag_when_speaker_is_none():
    excerpts = [
        {
            "source_type": "evidence",
            "source_id": "ev-1",
            "location": "00:00:30",
            "speaker": None,
            "content": "No speaker attribution.",
            "_detected_date": None,
        }
    ]
    formatted = build._format_excerpts(excerpts)
    assert "speaker=" not in formatted


def test_format_timestamp_formats_seconds_as_hh_mm_ss():
    assert build._format_timestamp(0) == "00:00:00"
    assert build._format_timestamp(65) == "00:01:05"
    assert build._format_timestamp(3725) == "01:02:05"
