#!/bin/bash
# PreToolUse hook on Bash. Blocks `git commit` / `git add` calls that look
# like they're staging something with SSN-shaped or other obviously
# sensitive patterns. This is a safety net, not a substitute for actual
# data-handling discipline — it will not catch everything and isn't a
# compliance control by itself.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

if echo "$COMMAND" | grep -qE '\bgit (add|commit)\b'; then
  # crude SSN-shaped pattern check across staged/working files.
  if git diff --cached -U0 2>/dev/null | grep -qE '[0-9]{3}-[0-9]{2}-[0-9]{4}'; then
    echo "Blocked: staged changes contain what looks like an SSN pattern. Confirm this is synthetic test data before committing, or remove it." >&2
    exit 2
  fi
fi

exit 0
