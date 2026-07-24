from core.db import get_client
from core.llm import generate

_PROMPT_TEMPLATE = """You are drafting a DEMAND LETTER DRAFT for a personal-injury case, for an attorney's review. This is a draft the attorney will revise and is never sent as-is.

Case: {case_name}

Below is the attorney-reviewed, signed-off chronology of events. Draft a professional demand letter that presents the factual narrative built ONLY from these chronology events. Requirements:
- Use only facts stated in the chronology below. Do not invent injuries, treatments, dates, parties, or events. Do not state a settlement/demand dollar amount -- that is the attorney's judgment.
- Structure: (1) a brief opening identifying this as a demand on behalf of the claimant, (2) a "Statement of Facts" section narrating the events in chronological order, citing each with its source reference, (3) an "Injuries and Treatment" section summarizing the medical course if the chronology contains medical events, (4) leave explicit bracketed placeholders the attorney must complete: "[ATTORNEY: state theory of liability]", "[ATTORNEY: itemize special damages -- medical bills, lost wages]", "[ATTORNEY: general damages / pain and suffering]", and "[ATTORNEY: total demand amount and response deadline]".
- Begin the document with a bold, unmistakable header line: "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE".
- Write in plain, professional prose. Do not fabricate letterhead, addresses, bar numbers, or a signature block beyond a placeholder "[ATTORNEY: signature block]".

CHRONOLOGY:
{events}
"""


def draft_demand_letter(case_id: str) -> dict:
    db = get_client()
    case = db.table("cases").select("*").eq("id", case_id).maybe_single().execute().data
    if not case:
        raise ValueError(f"case not found: {case_id}")
    if not case["chronology_signed_off"]:
        raise ValueError(
            "a demand letter can only be drafted from a signed-off chronology; "
            "sign off the chronology first"
        )
    entries = (
        db.table("chronology_entries")
        .select("*")
        .eq("case_id", case_id)
        .order("event_date")
        .execute()
        .data
    )
    if not entries:
        raise ValueError("no chronology entries to draft a demand letter from")

    body = generate(_PROMPT_TEMPLATE.format(case_name=case["name"], events=_format_events(entries)))

    existing = (
        db.table("demand_letters")
        .select("version")
        .eq("case_id", case_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
        .data
    )
    next_version = (existing[0]["version"] + 1) if existing else 1
    result = (
        db.table("demand_letters")
        .insert({"case_id": case_id, "body": body, "version": next_version})
        .execute()
    )
    return result.data[0]


def _format_events(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        if entry.get("source_document_id"):
            source = f"document {entry['source_document_id']} at {entry['source_location']}"
        else:
            source = f"evidence {entry['source_evidence_id']} at {entry['source_location']}"
        lines.append(f"- {entry['event_date']}: {entry['summary']} (source: {source})")
    return "\n".join(lines)
