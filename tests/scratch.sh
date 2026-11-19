#!/usr/bin/env bash
set -uo pipefail
git config --global user.name ci
git config --global user.email ci@example.com
work="${RUNNER_TEMP:-/tmp}/scratch"
bin/unslop new "${SCRATCH_TEMPLATE:-php}" "$work"
cd "$work" || exit 0
step() {
  echo "::group::$1"
  "${@:2}"
  local status=$?
  echo "::endgroup::"
  echo "RESULT $1: $status"
  return 0
}
step setup scripts/setup
git add -A && git commit -qm lock
step fast-check scripts/fast-check
step verify scripts/verify
[ -x scripts/mutation ] && step mutation scripts/mutation
exit 0
