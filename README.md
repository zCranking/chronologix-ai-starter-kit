# Chronologix AI — project starter kit

Drop this into a new or existing repo (copy everything, including the
dot-files — `.claude/` and `.mcp.json` won't show in a plain `ls`). Then:

## 1. Fill in the placeholders
Open `CLAUDE.md` and fill in the `[Fill in ...]` sections once you've
picked a stack: commands, architecture paragraph, tech stack. Everything
else in it (mission, domain vocabulary, compliance rules, working
agreements) is ready to use as-is.

## 2. Wire up the hook scripts
`scripts/post-edit-check.sh` currently does nothing but print a reminder.
Point it at your actual linter/test command once you have one.
`scripts/block-sensitive-commit.sh` works out of the box as a basic
safety net (blocks commits containing SSN-shaped strings) but isn't a
substitute for real data-handling discipline — see the Compliance section
of CLAUDE.md.

## 3. (Optional) install Graphify for cost control
Graphify maps the project (code, docs, schemas, and — relevant here — PDFs
and other case-adjacent files) into a queryable graph, so agents can query
structure instead of re-reading raw files every time. This is the single
highest-leverage thing to add once the repo has real size to it:

```bash
graphify install --project
graphify build .
```

Rebuild (`graphify build .`) after sessions with substantial structural
changes — CLAUDE.md already tells agents to do this and to prefer graph
queries over cold file reads.

## 4. Start working
```bash
claude
```
Then either:
- Type `/ship <description of the task>` and let the skill in
  `.claude/skills/ship/` run the plan → build → review-loop →
  accuracy-check sequence, or
- Paste `prompts/orchestrator-prompt.md` for the same flow without the
  skill (useful for the very first session, or outside Claude Code).

## What's in here

```
CLAUDE.md                        persistent project context (read every session)
PLANNING.md                      living roadmap + session log
.mcp.json                        MCP server config (template — empty until wired up)
api/                              FastAPI backend (ingest, extraction, chronology, flags)
web/                              Next.js frontend (attorney review UI)
supabase/                         Postgres/pgvector schema migrations
.claude/settings.json            hooks + permission guardrails
.claude/agents/
  builder.md                     implements one scoped increment at a time
  code-reviewer.md                read-only, checks code quality/security — PASS/FAIL
  accuracy-verifier.md            read-only, checks chronology output against source docs
  cost-auditor.md                read-only, flags wasteful tool/subagent usage
.claude/skills/ship/SKILL.md      /ship — the reusable plan/build/review-loop workflow
scripts/
  post-edit-check.sh              lint/test hook — needs your actual commands
  block-sensitive-commit.sh       basic guard against committing SSN-shaped data
docs/architecture.md              longer-form architecture notes (doesn't load every session)
prompts/orchestrator-prompt.md    standalone version of the /ship workflow, spelled out
```

## Why two review agents, not one
`code-reviewer` catches code problems: bad error handling, missing tests,
security issues. `accuracy-verifier` catches a completely different
failure mode specific to this product — a chronology that reads fine and
passes every test but contains a hallucinated fact, a misdated event, or a
citation that doesn't actually point to what it claims. A tool whose whole
value proposition is "trust this instead of doing it by hand" has to treat
that second failure mode as seriously as a crashing bug, which is why it's
a separate, mandatory step rather than a note inside the code review.
