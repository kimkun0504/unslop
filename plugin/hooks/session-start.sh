#!/usr/bin/env bash
set -uo pipefail
root=${CLAUDE_PROJECT_DIR:-}
[ -n "$root" ] && [ -f "$root/unslop.toml" ] || exit 0
here=$(cd "$(dirname "$0")" && pwd)
runner="$here/../bin/unslop"
[ -x "$runner" ] || runner="$here/unslop"
profile=$(sed -n 's/^profile *= *"\([^"]*\)".*/\1/p' "$root/unslop.toml" | head -n 1)
cat <<TEXT
# unslop

This repository uses unslop with the ${profile:-unknown} profile. Existing code keeps the findings recorded in .unslop/baseline.json; new and changed code meets the full bar.

- Run \`$runner check\` before you finish. The stop hook runs it too and will not let you stop while it fails. It rejects comments on lines you add, new suppressions or skipped tests, edits to existing tests, lint or type findings beyond the baseline, files that were formatted and no longer are, failing tests, and changed lines that no test covers.
- When it names a finding, fix the code. Never move code to dodge a count, never add a suppression, and never write code comments; make the code say it.
- Put new tests in new files, or append them after the last line of an existing test file. Do not edit or delete existing tests.
- Fixing old findings is welcome. Say so in your final message so a human can run \`unslop baseline\`.
- You cannot edit unslop.toml, .unslop/, .claude/, CI workflows, build files or lockfiles. If you need a change there, say what and why in your final message; a human applies it.
TEXT
