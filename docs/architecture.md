# Architecture

This is the detailed version. Keep CLAUDE.md's architecture section to one
paragraph and link here for anything longer — CLAUDE.md loads into every
session's context, this file only loads when someone (or an agent) opens it.

## Suggested shape for Phase 1 (edit once you've actually decided)

```
ingest/        # upload handling, OCR for scanned records, chunking
extraction/    # date/entity extraction from chunks
chronology/    # ordering, summarization, source-citation logic
flags/         # inconsistency detection
review/        # attorney review + edit UI, sign-off state machine
api/           # thin layer the frontend talks to
```

Suggested rule of thumb: nothing outside `chronology/` and `flags/` should
be calling an LLM directly. Keep the actual "generate a claim about a case"
logic centralized so it's the one place `accuracy-verifier` needs to focus
its scrutiny, rather than scattered LLM calls across the codebase that are
harder to audit for hallucination risk.

## Data flow (fill in once real)

1. [Document upload → storage]
2. [OCR / text extraction, if needed]
3. [Chunking + date/entity extraction]
4. [Chronology assembly + summarization]
5. [Flagging]
6. [Attorney review + sign-off]
7. [Final chronology available to the case team]

## Things worth deciding early, not organically
- Where the "source of truth" copy of each uploaded document lives, and
  how every chronology entry's citation points back to an exact
  location in it (page number, line, or timestamp for future video/audio).
- How a corrected/edited chronology entry is versioned — an attorney's
  manual correction should never be silently overwritten by a re-run of
  the pipeline.
