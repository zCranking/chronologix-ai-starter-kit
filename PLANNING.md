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
- [ ] Document ingestion (upload, OCR if needed, chunking)
- [ ] Chronology builder (date extraction, ordering, summarization)
- [ ] Inconsistency flagging (conflicting dates, contradicting statements)
- [ ] Every chronology entry traces to a source document and page/location
- [ ] Attorney review/edit UI before a chronology is marked final
- [ ] `accuracy-verifier` subagent run against a held-out test case with
      known ground truth, passing with zero hallucinated facts

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
