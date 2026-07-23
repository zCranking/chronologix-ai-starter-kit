# Chronologix AI Environment Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a working, empty-but-runnable Chronologix AI dev environment — FastAPI backend, Next.js frontend, Supabase schema, filled-in project docs, and a working lint hook — with nothing left as a placeholder.

**Architecture:** Five independent, non-overlapping increments (no two touch the same files), dispatched as parallel subagents: `api/` scaffold, `web/` scaffold, `supabase/` schema migration, CLAUDE.md/architecture.md fill-in + hook wiring, root housekeeping (`.gitignore`/README).

**Tech Stack:** Python 3.13 + FastAPI (backend), TypeScript + Next.js App Router (frontend), Supabase (Postgres + pgvector, Auth, Storage), Anthropic Claude (chronology generation — confined to `api/chronology/`), Voyage AI (chunk embeddings, `voyage-3`, 1024 dims — not specified in the design spec; picked here as Anthropic's recommended embedding partner since Anthropic doesn't offer its own embeddings API. Flagging this as a new decision, not a spec carryover.).

## Global Constraints

- Solo-dev environment: no CI pipeline, no team/role scaffolding.
- Synthetic/test data only — no BAA-grade hosting setup in this plan.
- Python 3.13.5 and Node 22.16 / npm 11.4.2 confirmed installed locally; no `uv`, no Supabase CLI, no Docker installed — use `npx` for Node-ecosystem tools and stdlib `venv`/`pip` for Python, nothing that requires a global install.
- `api/` owns all LLM calls; `chronology/` is the only module inside it allowed to call Claude (per `docs/architecture.md`).
- Every task must leave the repo in a state where `git status` is clean after its own commit — no stray untracked build artifacts.

---

### Task 1: FastAPI backend scaffold

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/main.py`
- Create: `api/core/__init__.py`
- Create: `api/core/config.py`
- Create: `api/ingest/__init__.py`
- Create: `api/extraction/__init__.py`
- Create: `api/chronology/__init__.py`
- Create: `api/flags/__init__.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/test_health.py`
- Create: `api/.env.example`
- Create: `api/.gitignore`

**Interfaces:**
- Consumes: nothing (first task in the `api/` tree).
- Produces: `app` (FastAPI instance) importable as `from main import app` when cwd is `api/`. `settings` (a `Settings` instance) importable as `from core.config import settings`, exposing `.supabase_url`, `.supabase_service_key`, `.anthropic_api_key` (all `str`, default `""`). Empty packages `ingest/`, `extraction/`, `chronology/`, `flags/` ready for later modules.

- [ ] **Step 1: Create `api/pyproject.toml`**

```toml
[project]
name = "chronologix-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic-settings>=2.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
    "ruff>=0.7",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["core*", "ingest*", "extraction*", "chronology*", "flags*"]
```

- [ ] **Step 2: Create the virtualenv and install dependencies**

```bash
cd api
python -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -e ".[dev]"
cd ..
```

Expected: installs without error; `api/.venv/Scripts/pytest.exe` and `api/.venv/Scripts/ruff.exe` exist afterward.

- [ ] **Step 3: Write the failing test**

Create `api/tests/__init__.py` (empty file).

Create `api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd api && .venv/Scripts/python.exe -m pytest -v && cd ..`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'main'` (`main.py` doesn't exist yet).

- [ ] **Step 5: Write the minimal implementation**

Create `api/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Chronologix API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd api && .venv/Scripts/python.exe -m pytest -v && cd ..`
Expected: PASS — `test_health_returns_ok PASSED`.

- [ ] **Step 7: Add the remaining scaffold files**

Create `api/core/__init__.py` (empty).

Create `api/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    anthropic_api_key: str = ""


settings = Settings()
```

Create `api/ingest/__init__.py`, `api/extraction/__init__.py`, `api/chronology/__init__.py`, `api/flags/__init__.py` — each an empty file.

Create `api/.env.example`:

```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
```

Create `api/.gitignore`:

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
*.egg-info/
```

- [ ] **Step 8: Verify tests and lint still pass**

Run: `cd api && .venv/Scripts/python.exe -m pytest -v && .venv/Scripts/python.exe -m ruff check . && cd ..`
Expected: pytest PASS, ruff reports no errors.

- [ ] **Step 9: Commit**

```bash
git add api/
git commit -m "feat: scaffold FastAPI backend with health check"
```

---

### Task 2: Next.js frontend scaffold

**Files:**
- Create: `web/` (entire directory, generated by `create-next-app`)

**Interfaces:**
- Consumes: nothing.
- Produces: a runnable Next.js app at `web/` (`npm run dev`, `npm run build`, `npm run lint` all defined in `web/package.json`). No other task depends on its internals yet — `web/` will call the FastAPI API in a later feature session, out of scope here.

- [ ] **Step 1: Generate the app**

```bash
npx --yes create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack --yes
```

Expected: creates `web/` with a working Next.js app, no interactive prompts left unanswered. If a prompt still appears, answer with the default (all defaults match the flags already passed).

- [ ] **Step 2: Verify the scripts exist**

Run: `cat web/package.json`
Expected: `scripts` block contains `"dev"`, `"build"`, `"lint"`.

- [ ] **Step 3: Verify the build succeeds**

Run: `npm run build --prefix web`
Expected: exits 0, prints a completed build summary (route list).

- [ ] **Step 4: Verify lint passes**

Run: `npm run lint --prefix web`
Expected: exits 0, no errors on the generated boilerplate.

- [ ] **Step 5: Commit**

```bash
git add web/
git commit -m "feat: scaffold Next.js frontend"
```

---

### Task 3: Supabase schema migration

**Files:**
- Create: `supabase/config.toml` (generated by `supabase init`)
- Create: `supabase/.gitignore` (generated by `supabase init`)
- Create: `supabase/migrations/00000000000001_init.sql`

**Interfaces:**
- Consumes: nothing.
- Produces: schema with tables `cases(id, name, created_at)`, `documents(id, case_id, storage_path, original_filename, status, uploaded_at)`, `chunks(id, document_id, page_number, content, embedding vector(1024), created_at)`, `chronology_entries(id, case_id, event_date, summary, source_document_id, source_location, version, edited_by_attorney, created_at)`, `flags(id, case_id, description, related_entry_ids uuid[], resolved, created_at)`. Later `api/ingest`, `api/chronology`, `api/flags` code will read/write these table names and columns.

- [ ] **Step 1: Initialize the Supabase project structure**

```bash
npx --yes supabase@latest init
```

Expected: creates `supabase/config.toml` and `supabase/.gitignore` at the repo root. If prompted to generate VS Code settings, decline (answer `n`) to avoid unrelated editor config churn.

- [ ] **Step 2: Verify the config was created**

Run: `test -f supabase/config.toml && echo "OK"`
Expected: `OK`.

- [ ] **Step 3: Write the initial migration**

Create `supabase/migrations/00000000000001_init.sql`:

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;

create table cases (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now()
);

create table documents (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    storage_path text not null,
    original_filename text not null,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'processed', 'failed')),
    uploaded_at timestamptz not null default now()
);

-- embedding dim matches Voyage AI voyage-3 (1024 dims); change here and in
-- the embedding call together if the embedding model ever changes.
create table chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    page_number int,
    content text not null,
    embedding vector(1024),
    created_at timestamptz not null default now()
);

create table chronology_entries (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    event_date date not null,
    summary text not null,
    source_document_id uuid not null references documents(id),
    source_location text not null,
    version int not null default 1,
    edited_by_attorney boolean not null default false,
    created_at timestamptz not null default now()
);

create table flags (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    description text not null,
    related_entry_ids uuid[] not null default '{}',
    resolved boolean not null default false,
    created_at timestamptz not null default now()
);

create index chunks_embedding_idx on chunks
    using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index documents_case_id_idx on documents (case_id);
create index chronology_entries_case_date_idx
    on chronology_entries (case_id, event_date);
create index flags_case_id_idx on flags (case_id);
```

- [ ] **Step 4: Sanity-check the migration file**

Run: `grep -c "^create table" supabase/migrations/00000000000001_init.sql`
Expected: `5`.

Run: `grep -c "^create index" supabase/migrations/00000000000001_init.sql`
Expected: `4`.

- [ ] **Step 5: Note the manual follow-up (not part of this task)**

This migration cannot be applied automatically — there's no live Supabase project yet and no Docker/local Postgres on this machine. Applying it requires the account holder: `npx supabase login`, `npx supabase link --project-ref <ref>` (from a project created at supabase.com), then `npx supabase db push`. Record this as an open item in `PLANNING.md`'s session log rather than treating it as done.

- [ ] **Step 6: Commit**

```bash
git add supabase/
git commit -m "feat: add Supabase schema migration for cases/documents/chunks/chronology/flags"
```

---

### Task 4: Fill in CLAUDE.md/architecture.md placeholders and wire the lint hook

**Files:**
- Modify: `CLAUDE.md`
- Modify: `scripts/post-edit-check.sh`

**Interfaces:**
- Consumes: nothing (references `api/` and `web/` paths that Tasks 1–2 create in parallel, but only at hook *runtime*, not at write time — the hook guards on those paths existing).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace the Tech stack section**

In `CLAUDE.md`, replace:

```
## Tech stack
[Fill in once decided — e.g. Python/FastAPI backend, Postgres, Next.js
frontend. Keep this section to 3-4 lines. Update it the day the stack
changes, not after.]
```

with:

```
## Tech stack
FastAPI (Python 3.13) backend in `api/`, handling ingest/OCR/chunking and
all LLM calls. Next.js (TypeScript, App Router) frontend in `web/` for the
attorney review UI. Supabase (Postgres + pgvector, Auth, Storage) for data.
Anthropic Claude for chronology generation/summarization; Voyage AI
(`voyage-3`) for chunk embeddings.
```

- [ ] **Step 2: Replace the Commands section**

Replace:

```
## Commands
```bash
[dev server command]
[test command]
[lint command]
[migration command]
```
```

with:

```
## Commands
```bash
# api/ (from repo root)
cd api && .venv/Scripts/python.exe -m uvicorn main:app --reload   # dev server
cd api && .venv/Scripts/python.exe -m pytest                      # test
cd api && .venv/Scripts/python.exe -m ruff check .                # lint

# web/ (from repo root)
npm run dev --prefix web      # dev server
npm run lint --prefix web     # lint
npm run build --prefix web    # build/typecheck

# supabase/ (from repo root)
npx supabase db push          # apply migrations to the linked project
```
```

- [ ] **Step 3: Replace the Architecture section**

Replace:

```
## Architecture (one paragraph, not a tour)
[e.g. "Documents land in /ingest, get OCR'd and chunked in the parser
service, chunks are embedded and stored in Postgres, the chronology
builder queries them in date order and calls the LLM for summarization.
Frontend reads finished chronologies from the API, nothing talks to the
LLM directly from the client."]
```

with:

```
## Architecture (one paragraph, not a tour)
Attorneys upload case documents through the `web/` Next.js UI; files land in
Supabase Storage. The `api/` FastAPI service OCRs and chunks each document
(`ingest/`), extracts dates/entities (`extraction/`), and stores chunks with
embeddings in Postgres/pgvector. `chronology/` queries chunks in date order
and calls Claude to build the chronology — this is the only module allowed
to call an LLM. `flags/` cross-checks chunks for inconsistencies. `web/`
reads the finished chronology from the API for attorney review, edit, and
sign-off; nothing in `web/` talks to the LLM or Supabase directly.
```

- [ ] **Step 4: Verify no placeholders remain**

Run: `grep -c "\[Fill in" CLAUDE.md`
Expected: `0`.

- [ ] **Step 5: Rewrite the lint hook**

Replace the full contents of `scripts/post-edit-check.sh`:

```bash
#!/bin/bash
# Runs after every Edit/Write. Keep this fast — it fires a lot.
#
# Exit 0 = ok, non-zero blocks nothing here (PostToolUse can't block the
# edit that already happened) but stderr output is surfaced back to Claude,
# which is enough to prompt a self-correction on the next turn.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

case "$FILE_PATH" in
  */api/*.py)
    # ponytail: lints the whole api/ tree instead of just the touched file —
    # fine at this size, switch to a single-file lint if it gets slow.
    [ -x api/.venv/Scripts/python.exe ] && (cd api && .venv/Scripts/python.exe -m ruff check .) >&2
    ;;
  */web/*.ts|*/web/*.tsx)
    [ -f web/package.json ] && (cd web && npx eslint . --quiet) >&2
    ;;
esac

exit 0
```

- [ ] **Step 6: Test the hook with a simulated `api/` edit**

Run: `echo '{"tool_input":{"file_path":"api/main.py"}}' | ./scripts/post-edit-check.sh; echo "exit: $?"`
Expected: `exit: 0` (works whether or not `api/.venv` exists yet, thanks to the `-x` guard).

- [ ] **Step 7: Test the hook with a simulated `web/` edit**

Run: `echo '{"tool_input":{"file_path":"web/src/app/page.tsx"}}' | ./scripts/post-edit-check.sh; echo "exit: $?"`
Expected: `exit: 0`.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md scripts/post-edit-check.sh
git commit -m "docs: fill in tech stack/commands/architecture, wire lint hook to ruff/eslint"
```

---

### Task 5: Root housekeeping — `.gitignore` and README

**Files:**
- Create: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Create the root `.gitignore`**

```
# Python
api/.venv/
**/__pycache__/
*.pyc
*.env
!.env.example

# Node
web/node_modules/
web/.next/

# Supabase
supabase/.branches/
supabase/.temp/

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Verify the ignore patterns actually work**

```bash
mkdir -p api/.venv web/node_modules
touch api/.venv/dummy web/node_modules/dummy .env
git check-ignore -q api/.venv/dummy && echo "api/.venv: ignored"
git check-ignore -q web/node_modules/dummy && echo "web/node_modules: ignored"
git check-ignore -q .env && echo ".env: ignored"
rm -rf api/.venv web/node_modules .env
```

Expected: all three "ignored" lines print.

- [ ] **Step 3: Update the README file tree**

In `README.md`, in the fenced block under `## What's in here`, change:

```
CLAUDE.md                        persistent project context (read every session)
PLANNING.md                      living roadmap + session log
.mcp.json                        MCP server config (template — empty until wired up)
```

to:

```
CLAUDE.md                        persistent project context (read every session)
PLANNING.md                      living roadmap + session log
.mcp.json                        MCP server config (template — empty until wired up)
api/                              FastAPI backend (ingest, extraction, chronology, flags)
web/                              Next.js frontend (attorney review UI)
supabase/                         Postgres/pgvector schema migrations
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore README.md
git commit -m "chore: add root .gitignore, update README file tree"
```

---

## After all tasks land

Update `PLANNING.md`'s session log with one line noting: stack decided and scaffolded (FastAPI/Next.js/Supabase), and that the Supabase migration still needs `supabase link` + `db push` run manually with the account holder's credentials before any ingest code can hit a real database. This is a Phase 1 setup entry, not a feature entry — don't check off any Definition of Done items yet.
