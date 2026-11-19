#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
export UNSLOP_TEST_PREFIX="$work/root"
export HOME="$work/home"
mkdir -p "$HOME/.claude"
case "$(uname -s)" in
  Darwin) managed="$UNSLOP_TEST_PREFIX/Library/Application Support/ClaudeCode" ;;
  *) managed="$UNSLOP_TEST_PREFIX/etc/claude-code" ;;
esac
hooks="$UNSLOP_TEST_PREFIX/usr/local/lib/claude-guard"
installer="$repo/install/install.sh"
passed=0
failed=0
ok() { passed=$((passed + 1)); }
no() { failed=$((failed + 1)); echo "FAIL $1"; }
assert() {
  local name=$1
  shift
  if "$@"; then ok; else no "$name"; fi
}
refute() {
  local name=$1
  shift
  if "$@"; then no "$name"; else ok; fi
}
contains() { grep -q -- "$1" "${@:2}" 2>/dev/null; }
same() { cmp -s "$1" "$2"; }
quiet() { "$@" > /dev/null 2>&1; }

mkdir -p "$managed"
printf '{"from":"it"}\n' > "$managed/managed-settings.json"
printf 'my own rules\n' > "$HOME/.claude/CLAUDE.md"

"$installer" system > /dev/null
"$installer" user > /dev/null
for h in guard-bash.sh protect-paths.sh stop-gate.sh; do assert "hook $h installed" test -x "$hooks/$h"; done
assert "managed settings installed" same "$managed/managed-settings.json" "$repo/global/managed-settings.json"
assert "existing managed settings backed up" contains '"it"' "$managed"/managed-settings.json.bak.*
assert "existing CLAUDE.md backed up" contains "my own rules" "$HOME"/.claude/CLAUDE.md.bak.*
assert "launcher installed" test -x "$hooks/unslop"
assert "check passes after install" quiet "$installer" check

"$installer" uninstall-system > /dev/null
"$installer" uninstall-user > /dev/null
refute "hooks removed" test -e "$hooks"
assert "managed settings restored from backup" contains '"it"' "$managed/managed-settings.json"
assert "CLAUDE.md restored from backup" contains "my own rules" "$HOME/.claude/CLAUDE.md"
refute "check fails after uninstall" quiet "$installer" check

"$installer" system > /dev/null
"$installer" user > /dev/null
printf '{"changed":"by hand"}\n' > "$managed/managed-settings.json"
printf 'edited after install\n' > "$HOME/.claude/CLAUDE.md"
"$installer" uninstall-system > /dev/null
"$installer" uninstall-user > /dev/null
assert "hand-edited managed settings kept" contains "by hand" "$managed/managed-settings.json"
assert "hand-edited CLAUDE.md kept" contains "edited after install" "$HOME/.claude/CLAUDE.md"

rm -rf "$UNSLOP_TEST_PREFIX" "$HOME/.claude"
mkdir -p "$HOME/.claude"
"$installer" system > /dev/null
"$installer" uninstall-system > /dev/null
refute "fresh install leaves no managed settings" test -e "$managed/managed-settings.json"
refute "fresh install leaves no hooks" test -e "$hooks"

echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
