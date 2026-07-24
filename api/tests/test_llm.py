from unittest.mock import MagicMock

from core import llm


def test_generate_sends_prompt_as_user_message_and_returns_text(monkeypatch):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="hello from claude")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    result = llm.generate("say hi")

    assert result == "hello from claude"
    fake_client.messages.create.assert_called_once_with(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": "say hi"}],
    )


def test_generate_passes_through_model_and_max_tokens_overrides(monkeypatch):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ok")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    llm.generate("prompt", model="claude-opus-4-6", max_tokens=100)

    fake_client.messages.create.assert_called_once_with(
        model="claude-opus-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "prompt"}],
    )


def test_strip_json_fence_passes_through_plain_json_unchanged():
    assert llm.strip_json_fence('[{"a": 1}]') == '[{"a": 1}]'


def test_strip_json_fence_strips_json_language_tagged_fence():
    assert llm.strip_json_fence('```json\n[{"a": 1}]\n```') == '[{"a": 1}]'


def test_strip_json_fence_strips_untagged_fence():
    assert llm.strip_json_fence('```\n[{"a": 1}]\n```') == '[{"a": 1}]'


def test_strip_json_fence_strips_surrounding_whitespace_around_fence():
    assert llm.strip_json_fence('  \n```json\n[{"a": 1}]\n```\n  ') == '[{"a": 1}]'
