# Chronologix AI — environment setup design

Date: 2026-07-23

## Context

Chronologix AI ingests case documents (medical records, depositions, incident
reports) for personal injury/civil litigation firms and produces an
attorney-reviewed, source-cited chronology with inconsistency flags. The repo
so far is a starter kit only: CLAUDE.md, PLANNING.md, `.claude/` agents and
`/ship` skill, and hook scripts, with tech stack and architecture left as
placeholders. This design covers standing up the actual dev environment for
Phase 1 (text-document chronology MVP) — not any chronology-building feature
work itself.

Constraints established during brainstorming:
- Solo build for now — optimize for one person moving fast, no team/role
  scaffolding yet.
- Synthetic/test data only for the near term — defer HIPAA-grade infra (BAA
  hosting, audit logging) until a real firm is onboarding.
- Should scale cleanly later without a rewrite.

## Stack decision

**Python/FastAPI backend + Next.js frontend + Supabase**, chosen over a
Next.js-only stack (weak PDF/OCR tooling in JS) and a Python monolith with a
server-rendered UI (less room for a polished attorney review experience).

- **`api/`** — FastAPI. Owns ingest, OCR, chunking, extraction, chronology
  generation, and flagging. `unstructured` (open source) handles PDF/DOCX
  parsing and OCR (via Tesseract) in one library instead of hand-rolling
  format-specific parsers. Anthropic SDK for LLM calls, confined to
  `chronology/` per architecture.md's existing rule — the only code path
  that talks to an LLM, keeping `accuracy-verifier`'s job scoped.
- **`web/`** — Next.js. Attorney review/edit/sign-off UI only. Talks to
  `api/`, never calls the LLM directly.
- **Supabase** — Postgres (+ pgvector for chunk embeddings), Auth, Storage
  for uploaded documents. Schema managed as migrations via the Supabase CLI
  against a hosted free-tier project — no local Docker stack.
- **Hosting**: Vercel (`web/`), Railway (`api/`), Supabase free tier. All
  synthetic data; BAA-grade hosting is a deliberate later decision, not part
  of this setup.

## Repo layout

```
chronologix-ai-starter-kit/        (repo root, flattened from a double-nested extract)
  api/
    ingest/          # upload handling, OCR, chunking
    extraction/       # date/entity extraction from chunks
    chronology/        # ordering, summarization, source-citation — only LLM call site
    flags/              # inconsistency detection
    core/                 # db models, config, Supabase auth verification
    main.py, pyproject.toml
  web/                 # Next.js — attorney review UI
  supabase/             # schema migrations
  .claude/, CLAUDE.md, PLANNING.md, docs/   # existing starter kit, placeholders filled in
```

## Data flow

Attorney uploads a document in `web` → stored in Supabase Storage → `api`
OCRs/parses it → chunks + embeddings land in Postgres/pgvector → `chronology/`
queries chunks in date order and calls Claude for extraction and
summarization → `flags/` cross-checks for inconsistencies → attorney reviews
and edits in `web`; edits are versioned, never silently overwritten by a
pipeline re-run.

## Error handling

Malformed/empty documents and OCR failures are caught at the `ingest/`
boundary and surfaced as a document-level status rather than swallowed or
allowed to silently produce a partial chronology.

## Testing

`pytest` in `api/`. Mandatory (not optional) for any logic in `extraction/`
or `chronology/` — date parsing, ordering, source traceability — per
`builder.md`'s existing instructions. Frontend tests deferred until there's
UI worth testing.

## Execution strategy: parallel agents

This setup decomposes into independent, non-overlapping increments — no two
touch the same files:
1. `api/` scaffold (FastAPI app skeleton, `pyproject.toml`, empty module
   dirs with a placeholder `__init__.py` each)
2. `web/` scaffold (Next.js app skeleton)
3. `supabase/` schema migration (initial tables: documents, chunks, cases,
   chronology_entries, flags)
4. CLAUDE.md / architecture.md placeholder fill-in (tech stack, commands,
   architecture paragraph) and `scripts/post-edit-check.sh` wired to real
   lint/test commands
5. `.gitignore`, root README housekeeping

Because these don't share state, they'll be dispatched as parallel subagents
during implementation rather than done serially, to minimize wall-clock time
on setup. Each increment still gets a `code-reviewer` pass per the existing
`/ship` workflow before being considered done; Graphify install is deferred
per the starter kit's own README ("once the repo has real size to it") — an
empty scaffold doesn't have enough structure yet to be worth graphing.

## Out of scope

No chronology-generation logic, no ingest/OCR implementation beyond the
scaffold, no attorney-review UI beyond the scaffold, no CI pipeline, no
deployment automation. This is environment setup only — Phase 1 feature work
follows in subsequent `/ship`-driven sessions.
