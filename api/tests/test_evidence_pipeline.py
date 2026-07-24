from unittest.mock import MagicMock

import pytest

from evidence import pipeline


def _fake_db(evidence_row):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = (
        evidence_row
    )
    db.storage.from_.return_value.download.return_value = b"file bytes"
    return db


def test_process_evidence_happy_path_inserts_segments_and_marks_transcribed(monkeypatch):
    evidence_row = {"id": "ev-1", "storage_path": "case-1/ev.mp4", "original_filename": "ev.mp4"}
    db = _fake_db(evidence_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(
        pipeline,
        "transcribe",
        lambda file_bytes: [
            {"start": 0.0, "end": 1.5, "speaker": 0, "text": "hello"},
            {"start": 1.5, "end": 3.0, "speaker": 1, "text": "hi there"},
        ],
    )
    monkeypatch.setattr(pipeline, "embed", lambda texts: [[0.1, 0.2], [0.3, 0.4]])

    pipeline.process_evidence("ev-1")

    db.table.return_value.insert.assert_called_once_with(
        [
            {
                "evidence_id": "ev-1",
                "start_time_seconds": 0.0,
                "end_time_seconds": 1.5,
                "speaker_label": "Speaker 0",
                "content": "hello",
                "embedding": [0.1, 0.2],
            },
            {
                "evidence_id": "ev-1",
                "start_time_seconds": 1.5,
                "end_time_seconds": 3.0,
                "speaker_label": "Speaker 1",
                "content": "hi there",
                "embedding": [0.3, 0.4],
            },
        ]
    )
    db.table.return_value.update.assert_called_once_with({"status": "transcribed"})


def test_process_evidence_marks_failed_and_reraises_on_evidence_fetch_error(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = (
        RuntimeError("supabase timeout")
    )
    monkeypatch.setattr(pipeline, "get_client", lambda: db)

    with pytest.raises(RuntimeError):
        pipeline.process_evidence("ev-1")

    db.table.return_value.update.assert_called_once_with({"status": "failed"})


def test_process_evidence_marks_failed_and_reraises_on_transcription_error(monkeypatch):
    evidence_row = {"id": "ev-1", "storage_path": "case-1/ev.mp4", "original_filename": "ev.mp4"}
    db = _fake_db(evidence_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)

    def raise_transcribe(file_bytes):
        raise ValueError("bad file")

    monkeypatch.setattr(pipeline, "transcribe", raise_transcribe)

    with pytest.raises(ValueError):
        pipeline.process_evidence("ev-1")

    db.table.return_value.update.assert_called_once_with({"status": "failed"})


def test_process_evidence_stores_segments_with_null_embedding_when_embed_fails(monkeypatch):
    evidence_row = {"id": "ev-1", "storage_path": "case-1/ev.mp4", "original_filename": "ev.mp4"}
    db = _fake_db(evidence_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(
        pipeline,
        "transcribe",
        lambda file_bytes: [
            {"start": 0.0, "end": 1.5, "speaker": 0, "text": "hello"},
            {"start": 1.5, "end": 3.0, "speaker": 1, "text": "hi there"},
        ],
    )

    def raise_embed(texts):
        raise RuntimeError("VOYAGE_API_KEY not set")

    monkeypatch.setattr(pipeline, "embed", raise_embed)

    pipeline.process_evidence("ev-1")

    db.table.return_value.insert.assert_called_once_with(
        [
            {
                "evidence_id": "ev-1",
                "start_time_seconds": 0.0,
                "end_time_seconds": 1.5,
                "speaker_label": "Speaker 0",
                "content": "hello",
                "embedding": None,
            },
            {
                "evidence_id": "ev-1",
                "start_time_seconds": 1.5,
                "end_time_seconds": 3.0,
                "speaker_label": "Speaker 1",
                "content": "hi there",
                "embedding": None,
            },
        ]
    )
    db.table.return_value.update.assert_called_once_with({"status": "transcribed"})


def test_process_evidence_skips_segment_insert_when_no_utterances(monkeypatch):
    evidence_row = {"id": "ev-1", "storage_path": "case-1/ev.mp4", "original_filename": "ev.mp4"}
    db = _fake_db(evidence_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(pipeline, "transcribe", lambda file_bytes: [])
    monkeypatch.setattr(pipeline, "embed", lambda texts: [])

    pipeline.process_evidence("ev-1")

    db.table.return_value.insert.assert_not_called()
    db.table.return_value.update.assert_called_once_with({"status": "transcribed"})


def test_process_evidence_handles_utterance_with_no_speaker(monkeypatch):
    evidence_row = {"id": "ev-1", "storage_path": "case-1/ev.mp4", "original_filename": "ev.mp4"}
    db = _fake_db(evidence_row)
    monkeypatch.setattr(pipeline, "get_client", lambda: db)
    monkeypatch.setattr(
        pipeline,
        "transcribe",
        lambda file_bytes: [{"start": 0.0, "end": 1.5, "speaker": None, "text": "hello"}],
    )
    monkeypatch.setattr(pipeline, "embed", lambda texts: [[0.1, 0.2]])

    pipeline.process_evidence("ev-1")

    db.table.return_value.insert.assert_called_once_with(
        [
            {
                "evidence_id": "ev-1",
                "start_time_seconds": 0.0,
                "end_time_seconds": 1.5,
                "speaker_label": None,
                "content": "hello",
                "embedding": [0.1, 0.2],
            }
        ]
    )
