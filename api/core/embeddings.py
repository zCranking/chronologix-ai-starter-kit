import voyageai

from core.config import settings

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def embed(texts: list[str], *, model: str = "voyage-3", input_type: str = "document") -> list[list[float]]:
    result = _get_client().embed(texts, model=model, input_type=input_type)
    return result.embeddings
