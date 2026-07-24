# Planning

This file is the living plan. The `builder` and `code-reviewer` subagents
should read it before starting work; whoever runs a session should update
it at the end. Keep entries short — this is a log and a map, not a report.

## Phase 1 — Document chronology MVP (COMPLETE, live-verified 2026-07-24)

Goal: given a folder of medical records, depositions, and incident reports
for one case, produce a date-ordered chronology with source citations and
flagged inconsistencies, reviewed and correctable by an attorney before
it's final.

Definition of done for this phase:
- [x] Document ingestion (upload, OCR if needed, chunking) — `api/ingest/`
- [x] Chronology builder (date extraction, ordering, summarization) —
      `api/extraction/dates.py` + `api/chronology/build.py`, built and
      tested against a mocked LLM (no Anthropic key yet — see below)
- [x] Inconsistency flagging (conflicting dates, contradicting statements) —
      `api/flags/detect.py`, same mocked-LLM caveat
- [x] Every chronology entry traces to a source document and page/location —
      enforced in `chronology/build.py`'s prompt + insert, not fabricated
- [x] Attorney review/edit UI before a chronology is marked final — `web/`
      (case list, upload, generate, inline edit, sign-off), build/lint
      clean, reviewed. Never exercised against a live backend (see below).
- [x] `accuracy-verifier` subagent run against a held-out test case with
      known ground truth, passing with zero hallucinated facts — **DONE
      2026-07-24, real credentials, real Claude/Voyage/Supabase, PASS.**
      Zero hallucinations, correct chronological ordering, correct
      source traceability, no dropped material events. Phase 1's
      Definition of Done is now genuinely met, not just unit-tested.

**Phase 1 is complete and live-verified**, not just built. All credentials
landed 2026-07-24; a full live end-to-end pass (real Supabase, real Claude,
real Voyage, real Tesseract OCR) surfaced and fixed 4 real bugs that no
amount of mocked unit testing could have caught:
1. Claude wraps JSON responses in markdown code fences even when told not
   to — `json.loads()` failed on every real chronology/flags call until
   `core.llm.strip_json_fence()` was added.
2. `build_chronology` had no protection against re-inserting a fresh entry
   for an event an attorney had already manually corrected — first found
   as silent duplication, fixed, but the first fix's dedup key
   (document + page) was too coarse and caused a second failure mode
   (dropping unrelated, never-edited events that happened to share a page
   with an edited one) — now keys on (document, page, event_date), with a
   documented remaining edge case (two distinct same-day events on one
   page would still collide; needs a real per-event id if that matters).
3. The combined edited+regenerated entry list wasn't sorted by date.
4. A failed/missing embedding call was taking down the entire document's
   ingest, even though chronology generation doesn't use embeddings for
   retrieval yet — decoupled so ingest succeeds regardless.

Also live-verified: real Tesseract OCR on an image-only (no text layer)
PDF, with Claude correctly parsing through realistic OCR character noise;
multi-document cases with correct cross-document chronological ordering
and per-entry source attribution.

## Current phase: Phase 2 — Multi-source ingestion

Goal: add video/audio (surveillance footage, recorded statements) as
inputs to the same chronology, with timestamp citations alongside the
existing page citations. Heavier human review built in by default, not
treated as a formality.

Definition of done for this phase:
- [x] Video/audio upload, transcription (Deepgram, diarized utterances
      with timestamps) — `api/core/transcription.py`, `api/evidence/`
- [x] Attorney confirmation gate before a transcript can feed into
      chronology generation — `evidence.confirmed_by_attorney`; enforced
      in `chronology/build.py`'s fetch, not just at the UI layer
- [x] Chronology entries can cite evidence (timestamp) as well as
      documents (page) — `chronology_entries.source_evidence_id`, a
      unified excerpt shape in `chronology/build.py`, DB check constraint
      enforcing exactly one source per entry
- [x] Evidence upload/confirm UI — `web/`, build/lint clean, reviewed
- [ ] `accuracy-verifier` pass specifically on an evidence-sourced (not
      just document-sourced) chronology entry, against known ground truth
- [ ] Real, non-synthetic video/audio test (everything verified so far
      used a synthetic TTS-generated WAV file and Windows SAPI — realistic
      for testing the pipeline mechanics, but not a substitute for a real
      recording with actual background noise, cross-talk, and accents)

**Live-verified 2026-07-24** (same session as Phase 1, immediately after):
real Deepgram transcription (Windows SAPI-generated synthetic speech, not
just silence/noise), correct diarization/timestamps, real Voyage
embeddings on segments, the confirmation gate actually blocking
unconfirmed evidence from `POST /cases/{id}/chronology` (verified empty
result pre-confirm, correct evidence-cited entry post-confirm with
`source_document_id: null` / `source_evidence_id` set / timestamp
location). Review caught one real gap, fixed: `_build_row` silently
routed any unrecognized `source_type` to the document column instead of
rejecting it — now raises.

## Future phases (not started — do not build ahead of this)

**Phase 3 — Move up the value chain.** Auto-drafted demand letters and
settlement packages generated from a finished chronology. Case value
benchmarking against similar past cases, once enough case history exists
to make that statistically meaningful.

**Phase 4 — Adjacent verticals and distribution.** Workers' comp and
medical malpractice case types (same document shapes, different
evaluation standard). Integration as an add-on inside case management
platforms (e.g. Clio, Filevine, Litify) rather than only direct sales.

**Open question, needs a deliberate decision, not a default:** whether to
ever sell a defense-side or insurer-facing version of this tool. Doing so
alongside the plaintiff-side product creates a conflict of interest that
needs a structural answer (separate entity, data walls, or picking a lane)
before it's built, not after.

## Session log
Add a dated one-line entry each session with anything worth remembering:
what shipped, what a reviewer caught, what got moved to CLAUDE.md.

- YYYY-MM-DD: [example] Kicked off repo, added starter kit.
- 2026-07-23: Environment setup (not a Phase 1 feature — none of the Definition
  of Done items above are started). Stack decided: FastAPI backend (`api/`),
  Next.js frontend (`web/`), Supabase Postgres/pgvector/Auth/Storage, Claude
  for chronology generation, Voyage AI (`voyage-3`) for chunk embeddings.
  Scaffolded all three plus the initial `cases/documents/chunks/
  chronology_entries/flags` schema migration; filled in CLAUDE.md's
  tech-stack/commands/architecture placeholders and wired
  `scripts/post-edit-check.sh` to ruff/eslint. Open item: the Supabase
  migration is written but not applied — needs `supabase login` + `supabase
  link --project-ref <ref>` + `supabase db push` with the account holder's
  credentials once a real project exists. Reviewer caught two real bugs in
  the lint-hook fill-in: its glob patterns didn't match bare relative paths
  (hook silently did nothing), and CLAUDE.md's architecture paragraph
  contradicted docs/architecture.md about which modules may call an LLM
  (chronology/ *and* flags/, not chronology/ alone) — both fixed and
  re-verified.
- 2026-07-23: Live Supabase project created (`chronologix-ai`, id
  `nhjmnuuhlwkurducenct`) and all migrations applied, including a firms/
  firm_members addition for the per-firm access model (cases now have a
  `firm_id`; real auth isn't wired up yet, so a placeholder dev firm is
  seeded — see the `ponytail:` comment in migration 3). RLS enabled
  default-deny on all tables (api/ uses the service-role key, bypasses it;
  web/ never talks to Supabase directly). Built most of Phase 1's backend:
  LLM/embedding provider wrappers (Anthropic + Voyage direct SDKs, not
  LiteLLM — LiteLLM has no Windows wheel and needs a Rust+MSVC toolchain to
  build from source, rejected as too heavy for this dev machine), ingest
  pipeline (pypdf/pymupdf/pytesseract/python-docx, Tesseract installed via
  winget), regex-based date extraction, chronology builder, flags
  detection, and the API routes tying them together. All built TDD via
  parallel `builder` dispatches + `code-reviewer` passes; reviewers caught
  and fixes landed for: a pipeline error-handling gap (a failed initial
  document fetch never marked the doc "failed", leaving it stuck
  "pending" forever) and a date-ordering bug (mixed-format dates came back
  grouped by regex pattern, not document order). Chronology/flags
  generation has never run against the real Claude API — no
  `ANTHROPIC_API_KEY` yet — so `accuracy-verifier` cannot run until that's
  provided. Attorney review/edit UI (`web/`) not started.
- 2026-07-24: All three credentials (`SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`,
  `VOYAGE_API_KEY`) provided. Built and shipped the attorney review UI
  (`web/`, case list/upload/generate/edit/sign-off), reviewed clean. Then
  ran a full live end-to-end pass against real Supabase/Claude/Voyage/
  Tesseract for the first time — found and fixed 4 real bugs unit tests
  couldn't catch (Claude's markdown-fenced JSON responses, chronology
  duplicate-on-regeneration in two successive failure modes, unsorted
  combined return value, embedding failure blocking ingest entirely — see
  Definition of Done section above for detail). `accuracy-verifier` then
  ran for real against a synthetic ground-truth case and PASSED: zero
  hallucinations, correct ordering, correct traceability. Also
  live-verified real OCR (image-only PDF, realistic character noise,
  Claude parsed through it correctly) and multi-document cross-referencing.
  Phase 1 Definition of Done is now fully checked off and genuinely
  verified, not just unit-tested. Test data cleaned from the live Supabase
  project afterward (3 small orphaned Storage files remain — Supabase
  blocks direct SQL deletion of storage objects; not worth a cleanup
  script for a free-tier dev project). Phases 2-4 intentionally not
  started — Phase 2 requires a scoping/design conversation before any
  code, and Phase 4 still has its flagged defense-side conflict-of-interest
  question open, unresolved by design (needs the account holder's decision).
- 2026-07-24 (same session, continued): started Phase 2 after a quick
  scoping check-in (one real decision: Deepgram for transcription, over
  AssemblyAI or building our own Whisper pipeline). Added
  `core/transcription.py`, `evidence/pipeline.py` (upload → Deepgram
  diarized transcription → segment → embed → store, same shape and same
  fetch-inside-try/embed-failure-tolerance fixes as the document
  pipeline), the `evidence`/`evidence_segments` schema with a check
  constraint enforcing every chronology entry cites exactly one of a
  document or evidence, the confirmation-gate endpoint, and the evidence
  upload/confirm UI. `chronology/build.py` now merges documents and
  confirmed evidence into one unified, date-sorted prompt. `DEEPGRAM_API_KEY`
  arrived mid-session; live-verified with a real Windows-SAPI-generated
  speech WAV file (not just silence) — real diarized transcription, real
  embeddings, the confirmation gate correctly blocking unconfirmed
  evidence, correct timestamp citations post-confirmation. Review caught
  and fixed one real gap: `_build_row` silently misrouted an unrecognized
  `source_type` to the document column instead of rejecting it. Remaining
  before Phase 2 can be called done the way Phase 1 is: an
  `accuracy-verifier` pass on an evidence-sourced entry specifically, and
  a real (non-synthetic) recording test — TTS speech validates pipeline
  mechanics but not real-world audio quality (background noise,
  cross-talk, accents). Phases 3-4 still untouched, same reasons as above.
