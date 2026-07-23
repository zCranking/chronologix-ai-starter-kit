from unittest.mock import MagicMock

from core import db


def test_get_client_caches_and_calls_create_client_once(monkeypatch):
    db._client = None
    sentinel = MagicMock()
    fake_create_client = MagicMock(return_value=sentinel)
    monkeypatch.setattr(db, "create_client", fake_create_client)

    first = db.get_client()
    second = db.get_client()

    fake_create_client.assert_called_once_with(
        db.settings.supabase_url, db.settings.supabase_service_key
    )
    assert first is sentinel
    assert second is sentinel
