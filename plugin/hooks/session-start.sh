#!/usr/bin/env bash
set -uo pipefail
root=${CLAUDE_PROJECT_DIR:-}
[ -n "$root" ] && [ -f "$root/unslop.toml" ] || exit 0
here=$(cd "$(dirname "$0")" && pwd)
runner="$here/../bin/unslop"
[ -x "$runner" ] || runner="$here/unslop"
profiles=$(sed -n 's/^ *profile *= *"\([^"]*\)".*/\1/p' "$root/unslop.toml" | sort -u | paste -sd, - | sed 's/,/, /g')
comments=$(sed -n 's/^ *comments *= *"\([a-z]*\)".*/\1/p' "$root/unslop.toml" | head -n 1)
if [ "$comments" = allow ]; then
  rule="Comments are allowed in this repository; keep them to why, not what."
else
  rule="Never write code comments; make the code say it."
fi
cat <<TEXT
# unslop

This repository uses unslop for ${profiles:-an unknown stack}; unslop.toml lists which folder each stack covers. Existing code keeps the findings recorded in .unslop/baseline.json; new and changed code meets the full bar.

- Run \`$runner check --fast\` before you finish. The stop hook runs it too and will not let you stop while it fails. It rejects new suppressions or skipped tests, edits to existing tests, lint, type and dead-code findings beyond the baseline, copy-pasted code, and files that were formatted and no longer are. Run \`$runner check\` for the full check with tests and changed-line coverage, which CI runs on every pull request.
- When it names a finding, fix the code. Never move code to dodge a count and never add a suppression. $rule
- Put new tests in new files, or append them after the last line of an existing test file. Do not edit or delete existing tests.
- You may add or update dependencies in package.json, pyproject.toml, Gradle or Maven files and their lockfiles; the pull request then needs a human's unslop-reviewed label. Change nothing else in those files.
- Fixing old findings is welcome. Say so in your final message so a human can run \`unslop baseline\`.
- You cannot edit unslop.toml, .unslop/, .claude/, CI workflows or tool configs. If you need a change there, say what and why in your final message; a human applies it.
TEXT
