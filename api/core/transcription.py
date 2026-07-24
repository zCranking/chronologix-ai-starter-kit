import deepgram

from core.config import settings

_client: deepgram.DeepgramClient | None = None

# Boosts recognition of terms Deepgram's general model tends to mishear or
# under-weight in legal proceedings, regardless of case type. Case-specific
# terms (medical conditions, party names) aren't included here -- they vary
# too much per case to guess generically; pass them via `keyterms` if a
# caller has case-specific vocabulary worth boosting.
DEFAULT_KEYTERMS = ["deposition", "plaintiff", "defendant", "witness", "testimony", "exhibit"]


def _get_client() -> deepgram.DeepgramClient:
    global _client
    if _client is None:
        _client = deepgram.DeepgramClient(api_key=settings.deepgram_api_key)
    return _client


def transcribe(file_bytes: bytes, *, model: str = "nova-3", keyterms: list[str] | None = None) -> list[dict]:
    response = _get_client().listen.v1.media.transcribe_file(
        request=file_bytes,
        model=model,
        diarize=True,
        utterances=True,
        punctuate=True,
        smart_format=True,
        keyterm=keyterms if keyterms is not None else DEFAULT_KEYTERMS,
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
