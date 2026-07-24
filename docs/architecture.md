# Architecture

This is the detailed version. Keep CLAUDE.md's architecture section to one
paragraph and link here for anything longer — CLAUDE.md loads into every
session's context, this file only loads when someone (or an agent) opens it.

## Repo shape (as built)

```
api/
  core/          # provider wrappers + shared infra — the only place external APIs are called
    db.py            # Supabase client (service role)
    llm.py            # Anthropic (Claude) — generate(), strip_json_fence()
    embeddings.py      # Voyage AI — embed()
    transcription.py    # Deepgram — transcribe()
    config.py            # Settings (pydantic-settings, reads api/.env)
  ingest/        # Phase 1: document upload → OCR/parse → chunk → embed → store
  evidence/      # Phase 2: video/audio upload → transcribe → segment → embed → store
  extraction/    # non-LLM date extraction from chunk/segment text (regex-based, deliberately not authoritative)
  chronology/    # ordering, summarization, source-citation — the only modules (with flags/) allowed to call an LLM
  flags/         # inconsistency detection
  main.py        # FastAPI routes — thin, delegates to the modules above
web/             # Next.js — attorney review UI (case list, upload, generate, edit, sign-off, evidence confirm)
supabase/migrations/   # schema, applied in order
```

Rule that's actually enforced, not just suggested: nothing outside
`chronology/` and `flags/` calls an LLM. `core/llm.py` is the only place
the Anthropic SDK is touched; `chronology/build.py` and `flags/detect.py`
are its only callers. This keeps `accuracy-verifier`'s scrutiny centralized
instead of chasing scattered LLM calls.

## Data flow (as built)

**Documents (Phase 1):**
1. Upload via `web/` → `POST /cases/{id}/documents` → stored in Supabase
   Storage bucket `documents`, a `documents` row created with `status:
   pending`, processing scheduled via FastAPI `BackgroundTasks`.
2. `ingest/pipeline.py`: download → `ingest/parse.py` (pypdf text layer,
   pymupdf+pytesseract OCR fallback for pages with no text layer,
   python-docx for `.docx`) → `ingest/chunk.py` (fixed-size chunking) →
   `core/embeddings.py` (Voyage; failure degrades to a null embedding,
   never blocks ingest — nothing reads embeddings for retrieval yet) →
   `chunks` rows stored, `documents.status: processed`.

**Evidence (Phase 2):**
1. Upload via `web/` → `POST /cases/{id}/evidence` → stored in Storage
   bucket `evidence`, an `evidence` row created with `status: pending`,
   `media_type` inferred from extension, `confirmed_by_attorney: false`.
2. `evidence/pipeline.py`: download → `core/transcription.py` (Deepgram,
   diarized utterances with timestamps) → same embedding-failure
   tolerance as documents → `evidence_segments` rows stored,
   `evidence.status: transcribed`.
3. **An unconfirmed transcript is invisible to chronology generation.**
   `POST /cases/{id}/evidence/{evidence_id}/confirm` sets
   `confirmed_by_attorney: true` — this is the Phase 2 "heavier review by
   default" requirement, not a formality. `chronology/build.py` only
   queries evidence where `confirmed_by_attorney = true`.

**Chronology (both source types, unified):**
1. `chronology/build.py` fetches chunks (all documents in the case) and
   evidence_segments (confirmed evidence only), normalizes both into a
   common excerpt shape (`source_type`, `source_id`, `location`, content),
   sorts by a regex-detected date (`extraction/dates.py` — a first pass,
   not authoritative; undated excerpts sort last).
2. One Claude call over the combined excerpts produces cited entries.
   `source_type` in the response routes to `source_document_id` (page
   citation) or `source_evidence_id` (`HH:MM:SS` timestamp citation) —
   the DB enforces exactly one is set via a check constraint. An
   unrecognized `source_type` raises rather than silently misrouting.
3. Regeneration never overwrites an attorney-edited entry — the delete
   step only clears `edited_by_attorney = false` rows before inserting a
   fresh set, keyed on `(source_id, location, event_date)` to avoid both
   duplicating unrelated events sharing a location and silently dropping
   an edited entry's sibling events. Return value is the edited + fresh
   entries combined, sorted by date — the API returns the true current
   state of the case, not a partial view.
4. `flags/detect.py` runs separately, over the finished chronology entries.
5. Attorney reviews in `web/`: edits via `PATCH` (bumps `version`, sets
   `edited_by_attorney`), signs off via `POST .../sign-off`
   (`chronology_signed_off` + timestamp on `cases`) — nothing is final
   without this.

## Decisions made (previously "decide early, not organically")

- Source-of-truth documents/evidence live in Supabase Storage
  (`documents`/`evidence` buckets); citations point back via
  `(source_document_id, source_location)` or `(source_evidence_id,
  source_location)` on `chronology_entries`.
- Attorney corrections are versioned via `chronology_entries.version` +
  `edited_by_attorney`; regeneration is edit-aware (see above), not a
  blind overwrite.
