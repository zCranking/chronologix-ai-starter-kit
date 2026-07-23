# Master orchestration prompt

The `/ship` skill in `.claude/skills/ship/` already encodes this workflow,
so day to day you can just type `/ship <task>`. Use this longer version
for the first session in a new repo, when working without the skill
installed, or when you want to hand the same instructions to a plain API
agent loop that doesn't have Claude Code's skill system.

---

We're working on Chronologix AI. Task: [DESCRIBE THE SPECIFIC TASK HERE].

Before writing any code:

1. Read CLAUDE.md and PLANNING.md in full if you haven't already.
2. Enter plan mode. Explore only what's relevant to this task — delegate
   broad codebase search to a subagent instead of reading widely in the
   main conversation. Do not edit anything yet.
3. Produce a written plan: which files you expect to touch, which
   subagents you'll delegate to and why, the order of operations, and the
   specific acceptance criteria a reviewer would check this against. If
   the task is bigger than one sitting, propose how to split it into
   increments. Show me the plan and wait for approval, unless I've told
   you to run fully autonomously.
4. Once approved, delegate implementation to the `builder` subagent, one
   increment at a time. Give it the acceptance criteria, not just the raw
   task description.
5. After each increment, delegate to `code-reviewer`. If it returns FAIL,
   send its exact feedback to `builder` and repeat. Don't report anything
   done on a review you haven't actually received back.
6. If this task touches chronology generation, summarization, date
   ordering, or inconsistency flagging, also delegate to
   `accuracy-verifier` after code-reviewer passes. This checks a different
   failure mode — hallucinated facts, dropped events, wrong dates — and a
   code-reviewer pass does not satisfy it.
7. If a reviewer can't reach PASS after 3 rounds on the same increment,
   stop and tell me what's stuck instead of continuing to loop.
8. Once everything required has passed: summarize what changed, what each
   reviewer caught and how it was resolved, and update PLANNING.md's
   session log. If you got something wrong more than once this session,
   add the correction to CLAUDE.md.
9. If the session ran long, optionally delegate to `cost-auditor` for a
   quick pass on whether any of it was wasteful — repeated reads that a
   Graphify graph query could have replaced, subagents on a stronger model
   than the task needed, and so on.
