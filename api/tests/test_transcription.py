from unittest.mock import MagicMock

from core import transcription


def _fake_utterance(start, end, speaker, text):
    utterance = MagicMock()
    utterance.start = start
    utterance.end = end
    utterance.speaker = speaker
    utterance.transcript = text
    return utterance


def test_transcribe_returns_utterance_segments(monkeypatch):
    fake_response = MagicMock()
    fake_response.results.utterances = [
        _fake_utterance(0.0, 4.5, 0, "Where were you on the morning of the incident."),
        _fake_utterance(4.5, 9.2, 1, "I was at the intersection around 8:15 AM."),
    ]
    fake_client = MagicMock()
    fake_client.listen.v1.media.transcribe_file.return_value = fake_response
    monkeypatch.setattr(transcription, "_get_client", lambda: fake_client)

    result = transcription.transcribe(b"fake audio bytes")

    assert result == [
        {"start": 0.0, "end": 4.5, "speaker": 0, "text": "Where were you on the morning of the incident."},
        {"start": 4.5, "end": 9.2, "speaker": 1, "text": "I was at the intersection around 8:15 AM."},
    ]
    fake_client.listen.v1.media.transcribe_file.assert_called_once_with(
        request=b"fake audio bytes",
        model="nova-3",
        diarize=True,
        utterances=True,
        punctuate=True,
        smart_format=True,
    )


def test_transcribe_returns_empty_list_when_no_utterances(monkeypatch):
    fake_response = MagicMock()
    fake_response.results.utterances = None
    fake_client = MagicMock()
    fake_client.listen.v1.media.transcribe_file.return_value = fake_response
    monkeypatch.setattr(transcription, "_get_client", lambda: fake_client)

    result = transcription.transcribe(b"silent audio")

    assert result == []
