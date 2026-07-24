import json

from core.db import get_client
from core.llm import generate, strip_json_fence
from extraction.dates import extract_dates

_PROMPT_TEMPLATE = """You are building a legal case chronology from source excerpts below.
Each excerpt is tagged with a source type ("document" or "evidence"), its source id, a location (a page number for documents, or a timestamp like "00:04:30" for evidence), and any date detected in it. Evidence excerpts may also show a speaker label.
Produce a JSON array of chronology entries, each with:
- "event_date": the date of the event in the excerpt, ISO format YYYY-MM-DD
- "summary": a concise one or two sentence summary of what happened, based only on this excerpt
- "source_type": "document" or "evidence", copied from the excerpt tag
- "source_id": the source id from the excerpt tag
- "source_location": the location from the excerpt tag

Only include facts explicitly stated in the excerpts. Do not infer, combine, or embellish. If an excerpt has no determinable date, omit it from the output. Return ONLY the JSON array, no other text.

EXCERPTS:
{excerpts}
"""


def build_chronology(case_id: str) -> list[dict]:
    db = get_client()
    excerpts = _fetch_case_excerpts(db, case_id)
    if not excerpts:
        return []
    sorted_excerpts = _attach_dates_and_sort(excerpts)
    prompt = _PROMPT_TEMPLATE.format(excerpts=_format_excerpts(sorted_excerpts))
    response = generate(prompt)
    entries = json.loads(strip_json_fence(response))
    fresh_rows = [_build_row(case_id, entry) for entry in entries]

    # An attorney's manual correction must never be silently overwritten by a
    # re-run (CLAUDE.md, docs/architecture.md) -- and just as importantly, a
    # re-run must not create a second, stale-vs-corrected entry for the same
    # excerpt either. Fetch already-edited entries first so both the
    # overwrite guard and the duplicate guard can key off them.
    #
    # ponytail: chunking/utterance-splitting is page/segment-granular, not
    # event-granular, so one source location routinely yields multiple
    # distinct events -- (source id, location) alone isn't a reliable "same
    # excerpt" key (a live test caught this for documents: editing one visit
    # on a page caused every other, unrelated visit on that same page to be
    # dropped on regeneration). Including event_date narrows this enough for
    # now; it would still under-dedup two genuinely different events at the
    # same location on the same date -- a real per-event identifier is the
    # proper fix if that collision turns out to matter in practice.
    edited_entries = (
        db.table("chronology_entries")
        .select("*")
        .eq("case_id", case_id)
        .eq("edited_by_attorney", True)
        .execute()
        .data
    )
    edited_keys = {_entry_key(e) for e in edited_entries}
    new_rows = [row for row in fresh_rows if _entry_key(row) not in edited_keys]

    inserted: list[dict] = []
    if new_rows:
        db.table("chronology_entries").delete().eq("case_id", case_id).eq(
            "edited_by_attorney", False
        ).execute()
        inserted = db.table("chronology_entries").insert(new_rows).execute().data

    return sorted(edited_entries + inserted, key=lambda e: e["event_date"])


def _build_row(case_id: str, entry: dict) -> dict:
    row = {
        "case_id": case_id,
        "event_date": entry["event_date"],
        "summary": entry["summary"],
        "source_location": entry["source_location"],
    }
    if entry["source_type"] == "evidence":
        row["source_evidence_id"] = entry["source_id"]
    else:
        row["source_document_id"] = entry["source_id"]
    return row


def _entry_key(row: dict) -> tuple:
    source_id = row.get("source_document_id") or row.get("source_evidence_id")
    return (source_id, row["source_location"], row["event_date"])


def _fetch_case_excerpts(db, case_id: str) -> list[dict]:
    excerpts: list[dict] = []

    documents = db.table("documents").select("id").eq("case_id", case_id).execute().data
    document_ids = [d["id"] for d in documents]
    if document_ids:
        chunks = db.table("chunks").select("*").in_("document_id", document_ids).execute().data
        for chunk in chunks:
            excerpts.append(
                {
                    "source_type": "document",
                    "source_id": chunk["document_id"],
                    "location": chunk["page_number"] if chunk["page_number"] is not None else "N/A",
                    "speaker": None,
                    "content": chunk["content"],
                }
            )

    # Phase 2's heavier-review requirement (PLANNING.md): only transcripts
    # an attorney has explicitly confirmed feed into chronology generation.
    evidence = (
        db.table("evidence")
        .select("id")
        .eq("case_id", case_id)
        .eq("confirmed_by_attorney", True)
        .execute()
        .data
    )
    evidence_ids = [e["id"] for e in evidence]
    if evidence_ids:
        segments = (
            db.table("evidence_segments").select("*").in_("evidence_id", evidence_ids).execute().data
        )
        for segment in segments:
            excerpts.append(
                {
                    "source_type": "evidence",
                    "source_id": segment["evidence_id"],
                    "location": _format_timestamp(segment["start_time_seconds"]),
                    "speaker": segment["speaker_label"],
                    "content": segment["content"],
                }
            )

    return excerpts


def _format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _attach_dates_and_sort(excerpts: list[dict]) -> list[dict]:
    for excerpt in excerpts:
        detected = extract_dates(excerpt["content"])
        excerpt["_detected_date"] = detected[0] if detected else None
    dated = sorted((e for e in excerpts if e["_detected_date"]), key=lambda e: e["_detected_date"])
    undated = [e for e in excerpts if not e["_detected_date"]]
    return dated + undated


def _format_excerpts(excerpts: list[dict]) -> str:
    lines = []
    for excerpt in excerpts:
        date_str = excerpt["_detected_date"].isoformat() if excerpt["_detected_date"] else "unknown"
        speaker_tag = f" speaker={excerpt['speaker']}" if excerpt["speaker"] else ""
        lines.append(
            f"[source_type={excerpt['source_type']} source_id={excerpt['source_id']} "
            f"location={excerpt['location']}{speaker_tag} detected_date={date_str}]\n"
            f"{excerpt['content']}\n"
        )
    return "\n".join(lines)
