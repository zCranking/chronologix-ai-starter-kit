# Session handoff — read this first

**Purpose:** a fresh, low-context session should be able to read *this file +
`CLAUDE.md` + `PLANNING.md`* and be fully oriented, without re-reading a long
prior conversation. Keep it current: update the "Current state" and "Open
directions" sections at the end of each working session.

Last updated: 2026-07-24.

---

## What Chronologix is (one paragraph)

A tool for plaintiff's personal-injury attorneys that turns case documents
(medical records, depositions, incident reports) and audio/video evidence
into a **verified, source-cited chronology** and a **demand-letter draft**.
Every generated fact traces to a source (document page or recording
timestamp), and nothing is final until an attorney signs off. The product's
entire trust proposition is provenance + human verification, so bugs that
silently drop, invent, or mis-cite a fact are treated as the highest
severity — higher than a crash. See `README.md` for the pitch,
`docs/architecture.md` for the data flow.

## Current state (what's built and verified)

- **Phase 1 — document chronology: COMPLETE, live-verified.** Ingest
  (PDF/DOCX + OCR fallback), regex date extraction, chronology builder,
  flagging, attorney review/edit/sign-off UI. `accuracy-verifier` PASS on
  real Claude output.
- **Phase 2 — video/audio evidence: COMPLETE, live-verified.** Deepgram
  transcription (diarized, timestamped), attorney-confirmation gate,
  unified chronology across documents + confirmed evidence with timestamp
  citations, evidence UI. `accuracy-verifier` PASS (it caught a real
  dropped-fact bug here — see RETROSPECTIVE).
- **Phase 3 — demand letters: COMPLETE, live-verified.** Drafting from a
  signed-off chronology only, no invented dollar amounts, `[ATTORNEY: …]`
  placeholders, versioned drafts, edit-survives-regeneration; API + UI.
- **Demo hardening: DONE.** CORS (a real demo-breaker), a provenance-themed
  UI redesign, `api/seed_demo.py` (a populated synthetic "Rivera v. Deng"
  demo case), and a real run guide in `README.md`.

**Verification bar in use:** unit tests (currently ~90, all green) are the
floor, not the proof. Every LLM-touching feature is additionally
**live-verified end-to-end against the real APIs**, and chronology output is
checked by the `accuracy-verifier` subagent. Mocks alone have repeatedly
passed while the real integration was broken (see RETROSPECTIVE).

## How to run it (see README for full detail)

1. `api/.env` must contain real `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   (service role, not anon), `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`,
   `DEEPGRAM_API_KEY`, and (Windows) `TESSERACT_CMD`. **These are gitignored
   and do NOT travel with the repo** — a fresh clone needs them re-supplied.
2. Backend: `cd api && .venv/Scripts/python.exe -m uvicorn main:app --reload`
   (recreate the venv with `pip install -e ".[dev]"` on a fresh clone).
3. Frontend: `npm install --prefix web && npm run dev --prefix web` → :3000.
4. Populate a demo: `cd api && .venv/Scripts/python.exe seed_demo.py`.

Live Supabase project id: `nhjmnuuhlwkurducenct` (name "chronologix-ai").
Schema is applied there and in `supabase/migrations/`. A placeholder dev
firm (`00000000-0000-0000-0000-000000000001`) stands in for real auth.

## Two open directions (both intentionally kept open)

The plaintiff-side lane is locked in; the defense-side/insurer question in
PLANNING.md is decided as **not pursuing it** — don't build a defense lane.
From here, two forward directions, either pickable independently:

### Direction A — demo-surface polish ("something to show people")
Lower-risk, no login wall, keeps the app easy to demo. Candidates:
- PDF/print export of a finished chronology and of a demand-letter draft
  (attorneys will want to hand these to someone).
- A short guided "sample walkthrough" or an in-app "Load demo case" button
  that runs the seed flow from the UI.
- Small UX: loading skeletons during the multi-second LLM calls, a clearer
  processing-status view for documents/evidence mid-ingest.

### Direction B — production hardening (toward real firms touching it)
Higher-value long-term, but adds a **login wall that makes demos harder**, so
sequence it when you're moving past demos.
- **Real auth** (Supabase Auth) replacing the dev-firm placeholder: login,
  JWT verification middleware in `api/` that resolves the caller's `firm_id`
  from `firm_members`, and dropping the hardcoded `DEV_FIRM_ID`.
- **Per-firm RLS policies** on all tables (RLS is currently enabled
  default-deny; `api/` uses the service-role key which bypasses it, so
  policies only matter once `web/` or end users hit Supabase directly). The
  `firms`/`firm_members` schema and `cases.firm_id` already exist for this.
- A real (non-synthetic) recording test for transcription, and the
  BAA/consent groundwork that must precede any real-PHI handling.

## Deferred, with reasons (don't build these without the prerequisite)

- **Case-value benchmarking** (Phase 3 tail) — needs a corpus of real closed
  cases with known outcomes; statistically meaningless pre-launch.
- **Deepgram fine-tuning** — needs a real labeled audio corpus (synthetic TTS
  would train on TTS artifacts). Keyterm boosting is already in as the
  no-training-data lever. Both of these, plus the RLS work above, touch real
  client data → need a signed BAA + consent/retention policy first.
- **Case-management integrations** (Clio/Filevine/Litify) — need real partner
  API credentials/partnerships that don't exist yet.

## Where the important logic lives

- Chronology generation (the safety-critical core): `api/chronology/build.py`.
  Contains the prompt, the document+evidence merge, dedup/overwrite
  protection, and source routing. Read this before touching chronology.
- The three LLM-calling modules (the ONLY ones allowed to call an LLM):
  `chronology/`, `flags/`, `demands/`. Provider wrappers: `api/core/llm.py`
  (Claude), `embeddings.py` (Voyage), `transcription.py` (Deepgram).
- API surface: `api/main.py` (thin route layer). UI: `web/src/app/` +
  `web/src/lib/api.ts` (typed client mirroring the API exactly).
