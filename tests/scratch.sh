#!/usr/bin/env bash
set -uo pipefail
git config --global user.name ci
git config --global user.email ci@example.com
template=${1:?usage: tests/scratch.sh <template>}
[ -d "templates/$template" ] || { echo "no template named $template; nothing to probe"; exit 0; }
fix=$(jq -r --arg t "$template" '.templates[] | select(.name == $t) | .autofix // empty' templates/catalog.json)
work="${RUNNER_TEMP:-/tmp}/scratch"
UNSLOP_OWNER=ci bin/unslop new "$template" "$work"
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
if [ -n "$fix" ]; then
  step autofix bash -c "$fix"
  echo "PATCH-BEGIN"
  git diff
  echo "PATCH-END"
  git add -A && git commit -qm autofix --allow-empty
fi
step fast-check scripts/fast-check
step verify scripts/verify
[ -x scripts/mutation ] && step mutation scripts/mutation
exit 0
