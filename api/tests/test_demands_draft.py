from unittest.mock import MagicMock

import pytest

from demands import draft


def _fake_db(case=None, entries=None, existing_versions=None):
    tables = {"cases": MagicMock(), "chronology_entries": MagicMock(), "demand_letters": MagicMock()}
    tables["cases"].select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = case
    tables["chronology_entries"].select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
        entries or []
    )
    tables["demand_letters"].select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = (
        existing_versions or []
    )
    db = MagicMock()
    db.table.side_effect = lambda name: tables[name]
    db.__tables__ = tables
    return db


def _signed_off_case(case_type="personal_injury"):
    return {
        "id": "case-1",
        "name": "Smith v. Jones",
        "chronology_signed_off": True,
        "case_type": case_type,
    }


def _entries():
    return [
        {
            "id": "e1",
            "case_id": "case-1",
            "event_date": "2024-01-03",
            "summary": "ER visit for back pain after collision.",
            "source_document_id": "doc-1",
            "source_evidence_id": None,
            "source_location": "1",
        }
    ]


def test_draft_demand_letter_raises_when_case_not_found(monkeypatch):
    db = _fake_db(case=None)
    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", MagicMock())
    with pytest.raises(ValueError, match="case not found"):
        draft.draft_demand_letter("case-1")


def test_draft_demand_letter_raises_when_chronology_not_signed_off(monkeypatch):
    case = {"id": "case-1", "name": "Smith v. Jones", "chronology_signed_off": False}
    db = _fake_db(case=case)
    gen = MagicMock()
    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", gen)
    with pytest.raises(ValueError, match="signed-off"):
        draft.draft_demand_letter("case-1")
    gen.assert_not_called()  # no wasted LLM call when the guard trips


def test_draft_demand_letter_raises_when_no_chronology_entries(monkeypatch):
    db = _fake_db(case=_signed_off_case(), entries=[])
    gen = MagicMock()
    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", gen)
    with pytest.raises(ValueError, match="no chronology entries"):
        draft.draft_demand_letter("case-1")
    gen.assert_not_called()


def test_draft_demand_letter_prompts_with_events_and_inserts_version_1(monkeypatch):
    db = _fake_db(case=_signed_off_case(), entries=_entries(), existing_versions=[])
    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE\n\nDear Counsel..."

    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", fake_generate)
    inserted = {"id": "dl-1", "case_id": "case-1", "body": "the draft", "version": 1, "edited_by_attorney": False}
    db.__tables__["demand_letters"].insert.return_value.execute.return_value.data = [inserted]

    result = draft.draft_demand_letter("case-1")

    assert "ER visit for back pain after collision." in captured["prompt"]
    assert "2024-01-03" in captured["prompt"]
    db.__tables__["demand_letters"].insert.assert_called_once_with(
        {"case_id": "case-1", "body": "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE\n\nDear Counsel...", "version": 1}
    )
    assert result == inserted


def test_draft_demand_letter_uses_workers_comp_prompt_for_workers_comp_case(monkeypatch):
    db = _fake_db(case=_signed_off_case(case_type="workers_comp"), entries=_entries(), existing_versions=[])
    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE"

    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", fake_generate)
    db.__tables__["demand_letters"].insert.return_value.execute.return_value.data = [
        {"id": "dl-1", "case_id": "case-1", "body": "x", "version": 1, "edited_by_attorney": False}
    ]

    draft.draft_demand_letter("case-1")

    assert "WORKERS' COMPENSATION BENEFITS CLAIM DRAFT" in captured["prompt"]
    assert "disability rating" in captured["prompt"]
    assert "pain and suffering" not in captured["prompt"]


def test_draft_demand_letter_uses_med_malpractice_prompt_for_med_malpractice_case(monkeypatch):
    db = _fake_db(case=_signed_off_case(case_type="med_malpractice"), entries=_entries(), existing_versions=[])
    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE"

    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", fake_generate)
    db.__tables__["demand_letters"].insert.return_value.execute.return_value.data = [
        {"id": "dl-1", "case_id": "case-1", "body": "x", "version": 1, "edited_by_attorney": False}
    ]

    draft.draft_demand_letter("case-1")

    assert "MEDICAL MALPRACTICE DEMAND LETTER DRAFT" in captured["prompt"]
    assert "standard of care" in captured["prompt"]


def test_draft_demand_letter_raises_on_unrecognized_case_type(monkeypatch):
    db = _fake_db(case=_signed_off_case(case_type="bogus"), entries=_entries(), existing_versions=[])
    gen = MagicMock()
    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", gen)
    with pytest.raises(ValueError, match="unrecognized case_type"):
        draft.draft_demand_letter("case-1")
    gen.assert_not_called()  # no wasted LLM call, and no wrongly-framed letter drafted


def test_draft_demand_letter_increments_version_when_prior_draft_exists(monkeypatch):
    db = _fake_db(case=_signed_off_case(), entries=_entries(), existing_versions=[{"version": 2}])
    monkeypatch.setattr(draft, "get_client", lambda: db)
    monkeypatch.setattr(draft, "generate", lambda prompt: "body text")
    db.__tables__["demand_letters"].insert.return_value.execute.return_value.data = [{"id": "dl-3", "version": 3}]

    draft.draft_demand_letter("case-1")

    args, _ = db.__tables__["demand_letters"].insert.call_args
    assert args[0]["version"] == 3
