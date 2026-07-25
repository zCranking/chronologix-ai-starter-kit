from core.db import get_client
from core.llm import generate

# Phase 4: same chronology/document shapes across case types (PLANNING.md),
# but the demand draft's evaluation standard and placeholders differ by
# case_type -- workers' comp has no liability/pain-and-suffering framing,
# med mal requires standard-of-care/breach/causation instead of a generic
# liability theory. Shared scaffold (header, facts-only rule, no dollar
# amounts, draft disclaimer) stays identical across all three.
_SHARED_RULES = """- Use only facts stated in the chronology below. Do not invent injuries, treatments, dates, parties, or events. Do not state a settlement/demand dollar amount -- that is the attorney's judgment.
- Begin the document with a bold, unmistakable header line: "DRAFT -- ATTORNEY REVIEW REQUIRED -- NOT FOR SERVICE".
- Write in plain, professional prose. Do not fabricate letterhead, addresses, bar numbers, or a signature block beyond a placeholder "[ATTORNEY: signature block]"."""

_CASE_TYPE_SECTIONS = {
    "personal_injury": """You are drafting a DEMAND LETTER DRAFT for a personal-injury case, for an attorney's review. This is a draft the attorney will revise and is never sent as-is.

Case: {case_name}

Below is the attorney-reviewed, signed-off chronology of events. Draft a professional demand letter that presents the factual narrative built ONLY from these chronology events. Requirements:
{shared_rules}
- Structure: (1) a brief opening identifying this as a demand on behalf of the claimant, (2) a "Statement of Facts" section narrating the events in chronological order, citing each with its source reference, (3) an "Injuries and Treatment" section summarizing the medical course if the chronology contains medical events, (4) leave explicit bracketed placeholders the attorney must complete: "[ATTORNEY: state theory of liability]", "[ATTORNEY: itemize special damages -- medical bills, lost wages]", "[ATTORNEY: general damages / pain and suffering]", and "[ATTORNEY: total demand amount and response deadline]".

CHRONOLOGY:
{events}
""",
    "workers_comp": """You are drafting a WORKERS' COMPENSATION BENEFITS CLAIM DRAFT, for an attorney's review. This is a draft the attorney will revise and is never sent as-is.

Case: {case_name}

Below is the attorney-reviewed, signed-off chronology of events. Draft a professional benefits-claim narrative built ONLY from these chronology events. This is a NO-FAULT benefits claim, not a liability demand -- do not argue fault, negligence, or a third party's liability.
{shared_rules}
- Structure: (1) a brief opening identifying this as a workers' compensation benefits claim on behalf of the claimant, (2) a "Statement of Facts" section narrating the work injury and treatment events in chronological order, citing each with its source reference, (3) a "Course of Treatment and Disability Status" section summarizing the medical course if the chronology contains medical events, (4) leave explicit bracketed placeholders the attorney must complete: "[ATTORNEY: average weekly wage and benefit calculation]", "[ATTORNEY: disability rating / impairment percentage]", "[ATTORNEY: authorized treating physician and MMI status]", and "[ATTORNEY: requested benefits and response deadline]".

CHRONOLOGY:
{events}
""",
    "med_malpractice": """You are drafting a MEDICAL MALPRACTICE DEMAND LETTER DRAFT, for an attorney's review. This is a draft the attorney will revise and is never sent as-is.

Case: {case_name}

Below is the attorney-reviewed, signed-off chronology of events. Draft a professional demand letter that presents the factual narrative built ONLY from these chronology events.
{shared_rules}
- Structure: (1) a brief opening identifying this as a demand on behalf of the patient/claimant, (2) a "Statement of Facts" section narrating the treatment events in chronological order, citing each with its source reference, (3) a "Standard of Care and Departure" section noting where the chronology reflects a departure from expected care, without asserting a legal conclusion, (4) leave explicit bracketed placeholders the attorney must complete: "[ATTORNEY: applicable standard of care]", "[ATTORNEY: breach and causation analysis]", "[ATTORNEY: damages -- medical bills, lost wages, general damages]", and "[ATTORNEY: total demand amount and response deadline]".

CHRONOLOGY:
{events}
""",
}


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

    case_type = case.get("case_type", "personal_injury")
    if case_type not in _CASE_TYPE_SECTIONS:
        raise ValueError(f"unrecognized case_type: {case_type!r}")
    template = _CASE_TYPE_SECTIONS[case_type]
    body = generate(
        template.format(
            case_name=case["name"],
            shared_rules=_SHARED_RULES,
            events=_format_events(entries),
        )
    )

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
