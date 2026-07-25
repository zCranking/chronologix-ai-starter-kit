import re

import anthropic

from core.config import settings

_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate(prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096) -> str:
    response = _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def strip_json_fence(text: str) -> str:
    """Claude (and other chat models) routinely wrap JSON output in a
    markdown code fence even when told not to, and sometimes appends
    explanatory prose after the closing fence. Find the fenced block
    anywhere in the response so trailing commentary doesn't break parsing;
    plain JSON with no fence passes through unchanged."""
    text = text.strip()
    match = _FENCE_RE.search(text)
    return match.group(1) if match else text
