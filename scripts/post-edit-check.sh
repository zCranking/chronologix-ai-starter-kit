#!/bin/bash
# Runs after every Edit/Write. Keep this fast — it fires a lot.
#
# Exit 0 = ok, non-zero blocks nothing here (PostToolUse can't block the
# edit that already happened) but stderr output is surfaced back to Claude,
# which is enough to prompt a self-correction on the next turn.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
# ponytail: ${FILE_PATH//\\//} silently no-ops in this MSYS bash despite
# looking correct — tr is the confirmed-working way to normalize backslashes
# to forward slashes here before matching.
FILE_PATH=$(printf '%s' "$FILE_PATH" | tr '\\' '/')

case "$FILE_PATH" in
  api/*.py|*/api/*.py)
    # ponytail: lints the whole api/ tree instead of just the touched file —
    # fine at this size, switch to a single-file lint if it gets slow.
    [ -x api/.venv/Scripts/python.exe ] && (cd api && .venv/Scripts/python.exe -m ruff check .) >&2
    ;;
  web/*.ts|web/*.tsx|*/web/*.ts|*/web/*.tsx)
    [ -f web/package.json ] && (cd web && npx eslint . --quiet) >&2
    ;;
esac

exit 0
