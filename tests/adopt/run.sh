#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
fixture=${1:?usage: tests/adopt/run.sh <fixture>}
work="${RUNNER_TEMP:-$(mktemp -d)}/adopt-$fixture"
rm -rf "$work"
mkdir -p "$work"
cd "$work"
git init -q -b main
git config user.name ci
git config user.email ci@example.com
source "$repo/tests/adopt/$fixture.sh"
build_legacy
git add -A
git commit -qm legacy
unslop() { uv run --quiet --project "$repo" unslop "$@"; }
init_arguments=(--profile "${fixture%%-*}")
if declare -F stacks >/dev/null; then
  read -r -a init_arguments <<<"$(stacks)"
fi
unslop init "${init_arguments[@]}"
git add -A
git commit -qm "Adopt unslop"
failures=0
reset() {
  git checkout -q -- .
  git clean -fdq -e node_modules -e .venv -e .gradle -e build -e target -e .terraform
}
expect_fail() {
  if unslop check > "$work/../out-$fixture.txt" 2>&1; then
    echo "MISSED: $1"
    failures=$((failures + 1))
  elif grep -q -- "$2" "$work/../out-$fixture.txt"; then
    echo "caught: $1 ($2)"
  else
    echo "WRONG CHECK for $1, expected: $2"
    tail -40 "$work/../out-$fixture.txt"
    failures=$((failures + 1))
  fi
  reset
}
expect_pass() {
  if unslop check > "$work/../out-$fixture.txt" 2>&1; then
    echo "passed: $1"
  else
    echo "FALSE ALARM: $1"
    tail -40 "$work/../out-$fixture.txt"
    failures=$((failures + 1))
  fi
  reset
}
expect_pass "legacy code as adopted"
cases
[ "$failures" -eq 0 ] || { echo "$failures adopt cases failed for $fixture"; exit 1; }
echo "all adopt cases passed for $fixture"
