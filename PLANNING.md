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
- [x] `accuracy-verifier` pass specifically on an evidence-sourced (not
      just document-sourced) chronology entry, against known ground truth
      — **first pass FAILED for real** (dropped a material fact), fixed,
      **second pass PASSED**. See below.
- [ ] Real, non-synthetic video/audio test (everything verified so far
      used a synthetic TTS-generated WAV file and Windows SAPI — realistic
      for testing the pipeline mechanics, but not a substitute for a real
      recording with actual background noise, cross-talk, and accents)

**Transcription accuracy roadmap** (partly done, rest deferred with reason):
- DONE: Deepgram keyterm boosting (`core/transcription.py`'s
  `DEFAULT_KEYTERMS` + a `keyterms` param) — boosts common legal terms
  immediately, needs no training data. This is the right first lever.
- DEFERRED, needs prerequisites: true Deepgram model fine-tuning on a
  domain corpus. Blocked on two things that don't exist yet, and building
  it now would be speculative: (1) a real labeled audio corpus — we're
  pre-launch with zero real case recordings, and fine-tuning on synthetic
  TTS would train the model on artifacts of the TTS voice, not real
  depositions; (2) compliance groundwork — real recordings are PHI/
  privileged, so a BAA with the transcription vendor and a defined
  consent/retention policy must precede pointing any training pipeline at
  real client audio (this is exactly the kind of vendor-data-flow decision
  CLAUDE.md's compliance section says to flag before wiring up). The
  practical path: once there's a modest volume of real, attorney-corrected
  transcripts (the confirm/edit steps already capture the correction
  signal), that corpus + a signed BAA is what unlocks fine-tuning — the
  data collection is a natural byproduct of normal use, not a separate
  effort.

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

**`accuracy-verifier` found a real bug, not a false alarm**: a deposition
audio (11 short Deepgram utterance segments, one continuous witness
answer) collapsed into one chronology entry that silently dropped the
witness's negative observation ("did not see the driver exit the vehicle
before police arrived"). Root cause: the shared prompt in
`chronology/build.py` instructed "a concise one or two sentence summary,"
which pushed Claude to compress and drop a fact rather than write a
longer one. Exactly the failure mode CLAUDE.md calls out as worse than an
obviously-incomplete result — a confident, complete-looking entry quietly
missing something an opposing counsel would seize on. Fixed by rewriting
the prompt to require every distinct material fact (including negative
observations) be covered, favoring length over omission. Re-verified live
(fact now present, nothing else regressed) and independently re-passed by
a second `accuracy-verifier` run. Also regression-checked against Phase
1's document case (same shared prompt) — no degradation, summaries are if
anything more complete than before.

## Current phase: Phase 3 — Move up the value chain

Goal: auto-drafted demand letters from a finished chronology, and (later)
case-value benchmarking against similar past cases.

Definition of done for this phase:
- [x] Demand-letter drafting from a SIGNED-OFF chronology — `api/demands/`,
      `demands/` is now a third LLM-calling module (governance updated in
      CLAUDE.md). Guards: no draft unless the chronology is signed off,
      the case exists, and there are entries — each guard trips before any
      LLM call. The draft draws facts only from the chronology, states no
      dollar amount, leaves `[ATTORNEY: ...]` placeholders (liability,
      damages, demand amount, signature), and is headed "DRAFT — ATTORNEY
      REVIEW REQUIRED". Drafts are versioned per-row; attorney edits (PATCH)
      bump version + set edited_by_attorney and survive regeneration.
- [x] Demand-letter API (generate/list/edit) + UI section — built, tested
- [x] Live end-to-end verified 2026-07-24: real Claude draft from a
      signed-off document chronology — every fact traced to the chronology
      (all 3 medical visits, correctly cited), zero invented dollar
      amounts, all attorney placeholders present, no fabricated
      bar numbers/letterhead. The sign-off gate correctly returned 400
      pre-signoff. Edit + regenerate versioning verified (attorney edit
      preserved as a separate versioned row through regeneration).
- [ ] Case-value benchmarking — **deferred, blocked on data, same as
      transcription fine-tuning.** Benchmarking a case's value against
      "similar past cases" is statistically meaningless with zero case
      history (we're pre-launch). PLANNING.md's own phrasing gates this on
      "once enough case history exists to make that statistically
      meaningful." Building it now would be a speculative similarity model
      over an empty corpus. Natural unlock: once real closed cases with
      known outcomes accumulate, that becomes the benchmarking corpus —
      and, like fine-tuning, it touches real client outcome data, so it
      needs the same BAA/consent groundwork before a pipeline points at it.
- [ ] `accuracy-verifier` was NOT separately spawned for the demand letter
      — the Opus orchestrator verified it inline (a 3-entry chronology vs.
      the drafted letter is unambiguous; spawning a second Opus agent for
      it would be redundant cost). For a genuinely ambiguous or
      higher-stakes draft, still run the dedicated verifier.

## Current phase: Phase 4 — Adjacent verticals and distribution

Goal: workers' comp and medical malpractice case types (same document
shapes, different evaluation standard). Integration as an add-on inside
case management platforms (e.g. Clio, Filevine, Litify) rather than only
direct sales.

Definition of done, split into what's actually buildable now vs. blocked:

- [x] **Adjacent case types (buildable, no new credentials needed):**
      `cases.case_type` (`personal_injury` | `workers_comp` |
      `med_malpractice`), migration `00000000000007_case_types.sql`,
      applied live. `POST /cases` validates and stores it.
      `demands/draft.py` now has three prompt sections sharing one scaffold
      (draft header, facts-only rule, no dollar amounts) but a distinct
      evaluation-standard section per type: workers_comp is framed as a
      no-fault benefits claim (average weekly wage, disability rating, MMI
      — no liability/pain-and-suffering language), med_malpractice requires
      a standard-of-care/breach/departure section instead of a generic
      liability theory. Chronology/flags generation is unchanged — same
      document shapes across all three types, per this phase's own framing.
      `web/` gets a case-type selector on creation and a badge (3 new
      accent colors extending the existing design-system tokens) on the
      case list and case detail header.
- [x] Live-verified 2026-07-25: seeded one demo case per type (see
      `seed_demo.py`, all synthetic), generated real chronologies, flags,
      and demand-letter drafts against live Claude/Voyage/Supabase.
      `accuracy-verifier` ran specifically against the med_malpractice case
      (the higher-stakes new path) — PASS, zero hallucinations, correct
      standard-of-care framing, no dollar amounts, all placeholders present.
      Also caught a real bug live (not case_type-specific, but surfaced by
      this case's content): `core.llm.strip_json_fence()` required the
      fenced block to span the entire response and broke when Claude
      appended explanatory prose after the closing fence on the
      med_malpractice flags call. Fixed (anchored `.match()` → unanchored
      `.search()`), regression-tested, re-verified live.
- [ ] **Case-management integrations (Clio/Filevine/Litify) — BLOCKED, not
      started.** These need real partner API credentials/OAuth apps that
      do not exist for this project (confirmed: no partner accounts, no
      API keys, nothing in `api/.env`/`.env.example` for any of the three).
      This was already flagged as a deferred item in
      `docs/SESSION-HANDOFF.md` before this session. Do not build a mock or
      placeholder integration against any of these platforms — an
      unauthenticated stub isn't a real feature and would need to be
      rebuilt against actual partner docs anyway. Unlocks when a partner
      relationship/API access exists; flag to the account holder if this
      becomes a priority.

**Open question — DECIDED 2026-07-24:** whether to sell a defense-side or
insurer-facing version. **Decision: no — plaintiff-side only.** Do not build
a defense lane. (Kept here for the record; the conflict-of-interest concern
that motivated the question no longer needs a structural answer because we're
committing to a single lane.)

## Where to go next (both directions intentionally open)

See `docs/SESSION-HANDOFF.md` for the detailed version. In short, two
independently-pickable directions from the current state:
- **A — demo-surface polish** (easier to show people, no login wall): PDF/print
  export of chronologies and demand letters, an in-app "load demo case"
  button, loading states during multi-second LLM calls.
- **B — production hardening** (toward real firms; adds a login wall so
  sequence it past the demo stage): real Supabase Auth replacing the
  `DEV_FIRM_ID` placeholder, per-firm RLS policies, a real non-synthetic
  recording test, and the BAA/consent groundwork any real-PHI handling needs.

## Session log
Add a dated one-line entry each session with anything worth remembering:
what shipped, what a reviewer caught, what got moved to CLAUDE.md.

- 2026-07-25: Phase 4 (partial) — adjacent case types. Added `case_type`
  (personal_injury/workers_comp/med_malpractice) to `cases`, migration
  applied live via MCP (CLI wasn't linked/logged-in in this environment).
  Case-type-aware demand-letter prompts in `demands/draft.py` (shared
  scaffold, distinct evaluation-standard section per type). `web/` gets a
  case-type selector + badge (3 new accent colors on the existing
  CSS-custom-property design system). `seed_demo.py` now seeds one
  synthetic case per type. Live-verified all three end to end against real
  Claude/Voyage/Supabase; `accuracy-verifier` PASSED on the med_malpractice
  letter (new/higher-stakes path). Live-testing caught a real bug in
  shared infra: `core.llm.strip_json_fence()`'s anchored regex broke when
  Claude appended prose after the closing JSON fence on the
  med_malpractice flags call — fixed (`.match()` on an anchored pattern →
  `.search()` on an unanchored one), regression-tested, re-verified live.
  `code-reviewer` caught one real gap: `demands/draft.py` silently fell
  back to the personal_injury prompt for any unrecognized case_type
  instead of raising (this repo's own established convention per
  `chronology/build.py`'s `_build_row`) — fixed to raise, test added.
  **Clio/Filevine/Litify integration NOT built** — blocked on nonexistent
  partner API credentials/partnerships, same blocker already on record in
  `docs/SESSION-HANDOFF.md`; do not build a mock integration against any
  of these. 97 tests green, `ruff`/`npm run lint`/`npm run build` clean.
- YYYY-MM-DD: [example] Kicked off repo, added starter kit.
- 2026-07-24 (session close): defense-side question DECIDED — plaintiff-side
  only, no defense lane. Demo-hardening pass: added CORS (a real
  demo-breaker the mock/curl tests never surfaced), redesigned the UI around
  the provenance-timeline identity (Spectral/Inter/JetBrains-Mono, dated
  timeline spine, source-colored markers, verify-state badges), added
  `api/seed_demo.py` (synthetic Rivera v. Deng demo case), and rewrote the
  README as a real run guide. Wrote `docs/SESSION-HANDOFF.md` (the
  read-first resume doc) and `docs/RETROSPECTIVE.md` (mistakes + process +
  Windows gotchas) so future/low-context sessions can pick up either open
  direction (demo polish vs. production auth/RLS) without re-reading the
  whole history. Ended with ~90 tests green, clean tree. Local servers
  stopped; repo to be pushed to a private GitHub remote by the owner.
- 2026-07-24 (continued): Phase 3 demand-letter drafting. Switched to an
  explicit two-tier model split at the user's request — Opus as
  orchestrator (design, decomposition, safety-critical judgment, review
  adjudication, the inline accuracy check on the drafted letter), Haiku
  for builders handed complete code (demands module, API endpoints),
  Sonnet for the prose-described UI build and all code reviews. Built the
  `demands/` module (third LLM-calling module, governance updated), schema,
  API, and UI; live-verified a real Claude-drafted demand letter that drew
  only on the chronology, stated no dollar figure, and carried all attorney
  placeholders. Case-value benchmarking deferred with reason (no case
  history corpus — same data blocker as transcription fine-tuning).
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
