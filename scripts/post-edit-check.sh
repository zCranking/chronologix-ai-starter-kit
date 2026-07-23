#!/bin/bash
# Runs after every Edit/Write. Keep this fast — it fires a lot.
# Fill in your actual linter once the stack is chosen, e.g.:
#   npx eslint --quiet . || exit 1
#   ruff check . || exit 1
#
# Exit 0 = ok, non-zero blocks nothing here (PostToolUse can't block the
# edit that already happened) but stderr output is surfaced back to Claude,
# which is enough to prompt a self-correction on the next turn.

echo "post-edit-check: no linter configured yet — edit scripts/post-edit-check.sh" >&2
exit 0
