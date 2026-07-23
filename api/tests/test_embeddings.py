from unittest.mock import MagicMock

from core import embeddings


def test_embed_returns_vectors_for_documents(monkeypatch):
    fake_result = MagicMock()
    fake_result.embeddings = [[0.1, 0.2], [0.3, 0.4]]
    fake_client = MagicMock()
    fake_client.embed.return_value = fake_result
    monkeypatch.setattr(embeddings, "_get_client", lambda: fake_client)

    result = embeddings.embed(["first chunk", "second chunk"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    fake_client.embed.assert_called_once_with(
        ["first chunk", "second chunk"], model="voyage-3", input_type="document"
    )


def test_embed_passes_through_input_type_for_query_embedding(monkeypatch):
    fake_result = MagicMock()
    fake_result.embeddings = [[0.9, 0.8]]
    fake_client = MagicMock()
    fake_client.embed.return_value = fake_result
    monkeypatch.setattr(embeddings, "_get_client", lambda: fake_client)

    embeddings.embed(["search query"], input_type="query")

    fake_client.embed.assert_called_once_with(
        ["search query"], model="voyage-3", input_type="query"
    )
