import deepgram

from core.config import settings

_client: deepgram.DeepgramClient | None = None


def _get_client() -> deepgram.DeepgramClient:
    global _client
    if _client is None:
        _client = deepgram.DeepgramClient(api_key=settings.deepgram_api_key)
    return _client


def transcribe(file_bytes: bytes, *, model: str = "nova-3") -> list[dict]:
    response = _get_client().listen.v1.media.transcribe_file(
        request=file_bytes,
        model=model,
        diarize=True,
        utterances=True,
        punctuate=True,
        smart_format=True,
    )
    utterances = response.results.utterances or []
    return [
        {
            "start": utterance.start,
            "end": utterance.end,
            "speaker": utterance.speaker,
            "text": utterance.transcript,
        }
        for utterance in utterances
    ]
