import re
from datetime import date

# ponytail: first-pass regex extraction only, not a complete date parser.
# Misses relative dates ("last Tuesday"), ambiguous formats without full
# context, and non-English dates. Upgrade path is chronology/'s LLM call,
# which sees full chunk context and can resolve what regex can't.

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_PATTERNS = [
    # ISO: 2024-01-15
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    # US slash: 01/15/2024 or 1/5/2024
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
    # Month DD, YYYY: January 15, 2024 / Jan 15, 2024
    (
        re.compile(
            r"\b(" + "|".join(_MONTHS) + r")\.?\s+(\d{1,2}),?\s+(\d{4})\b",
            re.IGNORECASE,
        ),
        lambda m: (int(m[3]), _MONTHS[m[1].lower()], int(m[2])),
    ),
]


def extract_dates(text: str) -> list[date]:
    found: list[tuple[int, date]] = []
    for pattern, to_ymd in _PATTERNS:
        for match in pattern.finditer(text):
            try:
                year, month, day = to_ymd(match)
                found.append((match.start(), date(year, month, day)))
            except ValueError:
                continue  # ponytail: skip malformed matches (e.g. day 32) rather than crash ingest
    found.sort(key=lambda item: item[0])
    return [d for _, d in found]
