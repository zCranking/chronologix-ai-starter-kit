# Planning

This file is the living plan. The `builder` and `code-reviewer` subagents
should read it before starting work; whoever runs a session should update
it at the end. Keep entries short — this is a log and a map, not a report.

## Current phase: Phase 1 — Document chronology MVP

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
- [ ] `accuracy-verifier` subagent run against a held-out test case with
      known ground truth, passing with zero hallucinated facts — **blocked
      on three missing credentials**: `SUPABASE_SERVICE_KEY` (needed just
      to run `api/` at all — a live smoke test this session hit
      `SupabaseException: supabase_key is required` on the very first
      request), `ANTHROPIC_API_KEY`, and `VOYAGE_API_KEY`. Every backend
      module above is unit-tested against mocks only and has NEVER run
      end-to-end against real Supabase, real Claude, or real Voyage. Do
      not treat the checked items above as "trustworthy chronology output
      achieved" —
      only as "the code path exists and is unit-tested."

## Future phases (not started — do not build ahead of this)

**Phase 2 — Multi-source ingestion.** Add video/audio (surveillance
footage, recorded statements) as inputs to the same chronology, with
timestamp syncing against the existing document-based timeline. Heavier
human review built in by default, not treated as a formality.

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
