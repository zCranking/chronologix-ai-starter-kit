---
name: ship
description: Use when the user asks to /ship, build, or implement a specific piece of work end to end. Plans first, delegates implementation to the builder subagent, loops code-reviewer (and accuracy-verifier when the change touches chronology/summarization/date logic) until both pass, then reports what changed. Do not use for pure Q&A or exploratory questions with no code change intended.
---

Follow this sequence for the task the user describes. Do not skip steps or
collapse them into one pass.

## 1. Plan
Read CLAUDE.md and PLANNING.md if not already in context. Enter plan mode
and explore only what's relevant (delegate broad exploration to the
built-in Explore subagent rather than reading files cold in the main
conversation). Produce a short plan: the files you expect to touch, which
subagents you'll use, and the acceptance criteria a reviewer should check
against. If the task is large, propose splitting it into increments rather
than planning the whole thing at once. Show the plan and wait for approval
unless the user has said to run autonomously.

## 2. Build
Delegate implementation to the `builder` subagent, one increment at a time.
Give it the specific acceptance criteria from the plan, not just the raw
task description.

## 3. Review loop
After each increment, delegate to `code-reviewer`. If it returns FAIL, send
its exact feedback back to `builder` and repeat. Do not proceed on a
partial or assumed review — wait for an actual PASS.

## 4. Accuracy check (conditional)
If the increment touches chronology generation, summarization, date
ordering, or inconsistency flagging, additionally delegate to
`accuracy-verifier` after `code-reviewer` passes. This step checks a
different failure mode (hallucinated or misdated facts) and is not
satisfied by a code-reviewer PASS. Loop the same way: FAIL sends specific
feedback back to `builder`.

## 5. Stop condition
If either reviewer cannot reach PASS after 3 rounds on the same increment,
stop and ask the user rather than continuing to iterate. Report exactly
what's still failing and why you think it's stuck.

## 6. Close out
Once all required reviewers pass: summarize what changed, what each
reviewer found along the way and how it was resolved, and update
PLANNING.md's session log. If a mistake got corrected more than once
during this task, add the correction to CLAUDE.md so it doesn't recur.
Optionally delegate to `cost-auditor` if the session ran long or the user
wants a cost check.
