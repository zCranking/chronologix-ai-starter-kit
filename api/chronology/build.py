import json

from core.db import get_client
from core.llm import generate, strip_json_fence
from extraction.dates import extract_dates

_PROMPT_TEMPLATE = """You are building a legal case chronology from source document excerpts below.
Each excerpt is tagged with its source document id, page number (or "N/A" for non-paginated documents), and any date detected in it.
Produce a JSON array of chronology entries, each with:
- "event_date": the date of the event in the excerpt, ISO format YYYY-MM-DD
- "summary": a concise one or two sentence summary of what happened, based only on this excerpt
- "source_document_id": the document id from the excerpt tag
- "source_location": the page number from the excerpt tag (or "N/A")

Only include facts explicitly stated in the excerpts. Do not infer, combine, or embellish. If an excerpt has no determinable date, omit it from the output. Return ONLY the JSON array, no other text.

EXCERPTS:
{excerpts}
"""


def build_chronology(case_id: str) -> list[dict]:
    db = get_client()
    chunks = _fetch_case_chunks(db, case_id)
    if not chunks:
        return []
    sorted_chunks = _attach_dates_and_sort(chunks)
    prompt = _PROMPT_TEMPLATE.format(excerpts=_format_excerpts(sorted_chunks))
    response = generate(prompt)
    entries = json.loads(strip_json_fence(response))
    fresh_rows = [
        {
            "case_id": case_id,
            "event_date": entry["event_date"],
            "summary": entry["summary"],
            "source_document_id": entry["source_document_id"],
            "source_location": entry["source_location"],
        }
        for entry in entries
    ]

    # An attorney's manual correction must never be silently overwritten by a
    # re-run (CLAUDE.md, docs/architecture.md) -- and just as importantly, a
    # re-run must not create a second, stale-vs-corrected entry for the same
    # excerpt either. Fetch already-edited entries first so both the
    # overwrite guard and the duplicate guard can key off them.
    edited_entries = (
        db.table("chronology_entries")
        .select("*")
        .eq("case_id", case_id)
        .eq("edited_by_attorney", True)
        .execute()
        .data
    )
    edited_locations = {(e["source_document_id"], e["source_location"]) for e in edited_entries}
    new_rows = [
        row
        for row in fresh_rows
        if (row["source_document_id"], row["source_location"]) not in edited_locations
    ]

    inserted: list[dict] = []
    if new_rows:
        db.table("chronology_entries").delete().eq("case_id", case_id).eq(
            "edited_by_attorney", False
        ).execute()
        inserted = db.table("chronology_entries").insert(new_rows).execute().data

    return edited_entries + inserted


def _fetch_case_chunks(db, case_id: str) -> list[dict]:
    documents = db.table("documents").select("id").eq("case_id", case_id).execute().data
    document_ids = [d["id"] for d in documents]
    if not document_ids:
        return []
    return db.table("chunks").select("*").in_("document_id", document_ids).execute().data


def _attach_dates_and_sort(chunks: list[dict]) -> list[dict]:
    for chunk in chunks:
        detected = extract_dates(chunk["content"])
        chunk["_detected_date"] = detected[0] if detected else None
    dated = sorted((c for c in chunks if c["_detected_date"]), key=lambda c: c["_detected_date"])
    undated = [c for c in chunks if not c["_detected_date"]]
    return dated + undated


def _format_excerpts(chunks: list[dict]) -> str:
    lines = []
    for chunk in chunks:
        date_str = chunk["_detected_date"].isoformat() if chunk["_detected_date"] else "unknown"
        page = chunk["page_number"] if chunk["page_number"] is not None else "N/A"
        lines.append(
            f"[document_id={chunk['document_id']} page={page} detected_date={date_str}]\n{chunk['content']}\n"
        )
    return "\n".join(lines)
