#!/usr/bin/env bash
set -uo pipefail
halt() { printf '{"continue":false,"stopReason":"%s"}\n' "$1"; exit 0; }
trap 'halt "stop-gate: internal error; work NOT verified"' ERR
command -v jq >/dev/null 2>&1 || halt "stop-gate: jq missing; work NOT verified"
input=$(cat)
root="${CLAUDE_PROJECT_DIR:-}"
[ -n "$root" ] && [ -f "$root/.claude/unslop.json" ] || exit 0
sid=$(printf '%s' "$input" | jq -er '.session_id | select(type == "string" and length > 0)' | tr -cd 'A-Za-z0-9_-') || halt "stop-gate: no session_id; work NOT verified"
[ -n "$sid" ] || halt "stop-gate: unusable session_id; work NOT verified"
cd "$root" || halt "stop-gate: project dir missing"
git rev-parse --git-dir >/dev/null 2>&1 || halt "stop-gate: not a git repository; work NOT verified"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/claude-stop-gate"
mkdir -p "$state_dir"
find "$state_dir" -type f -mtime +14 -exec rm -f {} + 2>/dev/null || true
ok_file="$state_dir/$sid.ok"
fail_file="$state_dir/$sid.fail"
total_file="$state_dir/$sid.total"
fingerprint=$(
  {
    git rev-parse --verify -q HEAD || echo no-head
    git diff HEAD --binary 2>/dev/null || git diff --cached --binary
    git ls-files -o --exclude-standard | git hash-object --stdin-paths
  } | git hash-object --stdin
)
[ "$fingerprint" = "$(cat "$ok_file" 2>/dev/null || true)" ] && exit 0
runner="./scripts/fast-check"
[ -x "$runner" ] || halt "stop-gate: $runner missing; work NOT verified"
limit=$(jq -r '.fast_check_seconds // 240' "$root/.claude/unslop.json" 2>/dev/null || echo 240)
case "$limit" in '' | *[!0-9]*) limit=240 ;; esac
[ "$limit" -ge 5 ] || limit=5
[ "$limit" -le 1700 ] || limit=1700
status=0
if command -v timeout >/dev/null 2>&1; then
  out=$(timeout "$limit" "$runner" 2>&1) || status=$?
elif command -v gtimeout >/dev/null 2>&1; then
  out=$(gtimeout "$limit" "$runner" 2>&1) || status=$?
else
  out=$(perl -e 'alarm shift; exec @ARGV or exit 127' "$limit" "$runner" 2>&1) || status=$?
  [ "$status" -eq 142 ] && status=124
fi
if [ "$status" -eq 124 ]; then
  halt "stop-gate: fast-check exceeded ${limit}s. A human can raise fast_check_seconds in .claude/unslop.json (up to 1700) or narrow the test command"
fi
if [ "$status" -eq 0 ]; then
  echo "$fingerprint" >"$ok_file"
  rm -f "$fail_file"
  exit 0
fi
last=""
n=0
[ -f "$fail_file" ] && read -r last n <"$fail_file"
if [ "$last" = "$fingerprint" ]; then n=$((n + 1)); else n=1; fi
echo "$fingerprint $n" >"$fail_file"
total=$(( $(cat "$total_file" 2>/dev/null || echo 0) + 1 ))
echo "$total" >"$total_file"
[ "$n" -ge 3 ] && halt "stop-gate: fast-check failed 3 times in a row with no code change; human review needed"
[ "$total" -ge 20 ] && halt "stop-gate: fast-check failed 20 times this session; human review needed"
printf 'fast-check failed (%s). Fix the cause; do not weaken tests, types or configs.\n%s\n' "attempt $total" "$(printf '%s\n' "$out" | tail -n 60)" >&2
exit 2
