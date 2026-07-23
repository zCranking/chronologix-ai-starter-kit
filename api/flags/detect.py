import json

from core.db import get_client
from core.llm import generate

_PROMPT_TEMPLATE = """You are reviewing a legal case chronology for inconsistencies.
Below are the chronology entries built from source documents. Identify only
genuine inconsistencies: conflicting dates for what appears to be the same
event, or contradicting statements about the same fact across different
source documents. Do not flag things that are merely different, unrelated
events -- only flag genuine conflicts.

Return a JSON array of flags, each with:
- "description": a concise description of the inconsistency and which entries conflict
- "related_entry_ids": array of the chronology entry ids involved

If there are no genuine inconsistencies, return an empty array.

CHRONOLOGY ENTRIES:
{entries}
"""


def detect_flags(case_id: str) -> list[dict]:
    db = get_client()
    entries = db.table("chronology_entries").select("*").eq("case_id", case_id).execute().data
    if not entries:
        return []
    prompt = _PROMPT_TEMPLATE.format(entries=_format_entries(entries))
    response = generate(prompt)
    flags = json.loads(response)
    rows = [
        {
            "case_id": case_id,
            "description": flag["description"],
            "related_entry_ids": flag["related_entry_ids"],
        }
        for flag in flags
    ]
    if rows:
        db.table("flags").insert(rows).execute()
    return rows


def _format_entries(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        lines.append(f"[id={entry['id']} date={entry['event_date']}]\n{entry['summary']}\n")
    return "\n".join(lines)
