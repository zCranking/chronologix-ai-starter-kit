# Retrospective — learnings from the build

Hard-won lessons from building Phases 1–3. The point of this file is that a
future session (or a teammate) shouldn't re-pay for these. The most
important, always-applicable ones are also distilled into `CLAUDE.md`'s
working agreements; this file keeps the full detail and the "why."

---

## The single biggest lesson: unit tests are the floor, live verification is the proof

~90 unit tests were green while **multiple real integrations were broken**.
Mocks return clean, well-formed data by construction, so they cannot catch
how a real dependency actually behaves. Every one of these shipped past a
full green suite and was only caught by running the real thing end-to-end:

- **Claude wraps JSON in markdown code fences** (` ```json … ``` `) even when
  the prompt says "return ONLY the JSON array." `json.loads()` failed on
  every real chronology/flags call. Fix: `core.llm.strip_json_fence()`.
  Mocks returned bare JSON, so all tests passed.
- **A demand/chronology summary silently dropped a material fact.** A
  deposition answer split into 11 short transcript utterances got compressed
  into one entry that omitted the witness's negative observation ("did not
  see the driver exit the vehicle"). The `accuracy-verifier` subagent caught
  it against ground truth; no unit test could have. Root cause was a prompt
  saying "concise one or two sentence summary" trading completeness for
  brevity. This is the exact failure mode the product must fear most: a
  confident, complete-looking output quietly missing something.
- **Embedding failure took down the whole ingest.** A missing/failed Voyage
  call aborted document processing entirely, even though chronology doesn't
  use embeddings for retrieval yet. Fixed to degrade to a null embedding.
- **Chronology dedup was wrong twice, found only live.** First a re-run
  duplicated an attorney-edited event; the fix (`(source_id, location)` key)
  was too coarse and then *dropped* unrelated events sharing a page; the real
  fix keys on `(source_id, location, event_date)`. Iterative, live-only.
- **CORS was missing.** The browser blocks every cross-origin UI→API call
  without it — but `curl` and FastAPI's `TestClient` don't enforce CORS, so
  it was invisible until the app actually ran in a browser.
- **A credential was never actually set.** `SUPABASE_SERVICE_KEY` sat as a
  placeholder comment; the API couldn't start. Caught only at the first live
  smoke test, not by any test.

**Takeaway, now a working agreement:** for anything touching an LLM, a real
API, or the browser, a passing mock suite is not "done." Run it live against
the real thing, and for chronology/flag/demand output, run `accuracy-verifier`
against known ground truth.

## What worked well (keep doing)

- **Model-tier orchestration** (introduced mid-session at the user's request,
  worth keeping): Opus orchestrates (design, decomposition, safety-critical
  judgment, adjudicating reviews, inline accuracy checks); Haiku builds when
  handed complete code (transcription-level work); Sonnet builds
  prose-described work (UI) and runs all code reviews; `accuracy-verifier`
  runs on Opus only when a factual judgment genuinely needs it. Cheaper and
  no quality loss, because the expensive model spends its tokens on
  orchestration, not typing out code that was already specified.
- **Parallel, file-disjoint builder dispatches.** When tasks touch different
  files (e.g. `chronology/` and `flags/`), building them in parallel worked
  cleanly. Controller (Opus) commits sequentially afterward to avoid
  concurrent writes to the shared git index — builders never run `git`.
- **Strict TDD** (red before green, every time) kept the unit layer honest.
- **Per-increment commit + review gate.** Every increment: build → review
  (code-reviewer) → fix → commit. Caught real bugs (the pipeline
  fetch-outside-try bug, the coarse dedup key, the source_type mis-routing).
- **Deferring speculative work with an explicit reason** rather than building
  on absent data (benchmarking, fine-tuning, integrations). Writing down
  *why* and *what unblocks it* is more valuable than a half-built feature.

## Mistakes and process fixes

- **Wrong parent-commit hash to reviewers, repeatedly.** Handing a reviewer
  the wrong `parent..HEAD` range produced false-positive "scope creep"
  findings (the diff appeared to include unrelated files). Fix, now standard:
  run `git log --oneline` and confirm the real parent before dispatching any
  review, and tell the reviewer to verify it too.
- **Piping a critical write to `/dev/null`.** A `sign-off` POST hit a
  transient Supabase connection drop (`WinError 10054`) and silently didn't
  land; the failure was hidden because the output was discarded. Fix: don't
  discard output of state-changing calls; confirm they actually took effect
  (re-read the row).
- **Designing around a dependency before confirming it installs.** LiteLLM
  (no Windows wheel → needs a Rust+MSVC toolchain) and `unstructured` (huge,
  minutes-long import, needs system binaries) were both chosen, then
  abandoned after they failed to install/run on this machine. Fix: verify a
  new dependency actually installs and imports on the target platform
  *before* writing code against it. Ended up on direct SDKs (`anthropic`,
  `voyageai`, `deepgram-sdk`) and lightweight parsers (`pypdf`, `pymupdf`,
  `pytesseract`, `python-docx`).

## Windows / environment gotchas (this machine)

- No LiteLLM/unstructured wheels — avoid Python libs without prebuilt Windows
  wheels unless a compiler toolchain is acceptable.
- Tesseract installed via `winget` (`UB-Mannheim.TesseractOCR`); its path is
  passed to the app via `TESSERACT_CMD` in `.env` (a Linux deploy with
  tesseract on PATH won't need it).
- Stop dev servers with `taskkill //PID <pid> //F` (no `pkill`); find the pid
  via `netstat -ano | grep :PORT | grep LISTENING`.
- In MSYS bash, `${VAR//\\//}` parameter expansion silently no-ops on
  backslashes — use `tr '\\' '/'` instead (this bit the lint-hook fix).
- `/tmp` differs between `curl` (Windows temp) and Python — write shared
  temp files to the session scratchpad dir, not `/tmp`.
- Start a dev server, then actually wait for it to be ready before curling
  it — an early request against a not-yet-listening server returns empty and
  cascades (an empty case_id went into later URLs once).
