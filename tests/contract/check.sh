#!/usr/bin/env bash
set -uo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo" || exit 2
problems=0
fail() {
  echo "contract: $1" >&2
  problems=$((problems + 1))
}

catalog=templates/catalog.json
jq -e '.templates | length > 0' "$catalog" >/dev/null || { echo "contract: $catalog missing or empty" >&2; exit 2; }
mapfile -t names < <(jq -r '.templates[].name' "$catalog")

while IFS= read -r dir; do
  name=$(basename "$dir")
  printf '%s\n' "${names[@]}" | grep -qx -- "$name" || fail "templates/$name is not listed in $catalog"
done < <(find templates -mindepth 1 -maxdepth 1 -type d | sort)

for workflow in .github/workflows/*.yml templates/*/.github/workflows/*.yml; do
  while IFS= read -r ref; do
    [[ "$ref" =~ @[0-9a-f]{40}$ ]] || fail "$workflow uses an action not pinned to a commit SHA: $ref"
  done < <(sed -n 's/^ *- *uses: *\([^ ]*\).*/\1/p; s/^ *uses: *\([^ ]*\).*/\1/p' "$workflow")
  grep -q 'persist-credentials: false' "$workflow" || fail "$workflow must check out with persist-credentials: false"
  grep -Eq '^permissions:' "$workflow" || fail "$workflow must declare top-level permissions"
done

for name in "${names[@]}"; do
  t="templates/$name"
  [ -d "$t" ] || { fail "$name is in the catalog but $t does not exist"; continue; }
  for f in CLAUDE.md .gitignore .github/workflows/ci.yml; do
    [ -f "$t/$f" ] || fail "$name is missing $f"
  done
  for s in setup fast-check verify; do
    [ -x "$t/scripts/$s" ] || fail "$name is missing executable scripts/$s"
  done
  mutation=$(jq -r --arg n "$name" '.templates[] | select(.name == $n) | .gates.mutation' "$catalog")
  if [ "$mutation" = null ]; then
    [ ! -e "$t/scripts/mutation" ] || fail "$name has scripts/mutation but the catalog says it has no mutation gate"
  else
    [ -x "$t/scripts/mutation" ] || fail "$name declares a mutation gate but has no executable scripts/mutation"
    grep -q 'scripts/mutation' "$t/.github/workflows/ci.yml" || fail "$name CI does not run scripts/mutation"
  fi
  grep -q 'scripts/check-comments' "$t/scripts/fast-check" || fail "$name fast-check does not run scripts/check-comments"
  grep -q 'scripts/check-diff' "$t/scripts/fast-check" || fail "$name fast-check does not run scripts/check-diff"
  grep -q 'scripts/fast-check' "$t/scripts/verify" || fail "$name verify does not run scripts/fast-check"
  ci="$t/.github/workflows/ci.yml"
  grep -Eq '^  verify:' "$ci" || fail "$name CI has no job named verify (the ruleset requires it)"
  grep -q 'fetch-depth: 0' "$ci" || fail "$name CI must fetch full history for check-diff"
  grep -q 'run: scripts/setup' "$ci" || fail "$name CI does not run scripts/setup"
  grep -q 'run: scripts/verify' "$ci" || fail "$name CI does not run scripts/verify"
  grep -q 'tests-reviewed' "$ci" || fail "$name CI does not honour the tests-reviewed label"
  lines=$(wc -l <"$t/CLAUDE.md")
  [ "$lines" -le 25 ] || fail "$name CLAUDE.md has $lines lines; keep it at 25 or fewer"
  grep -q 'scripts/fast-check' "$t/CLAUDE.md" || fail "$name CLAUDE.md does not name scripts/fast-check"
  grep -qx '\.env' "$t/.gitignore" || fail "$name .gitignore does not ignore .env"
  while IFS= read -r shared; do
    [ ! -e "$t/$shared" ] || fail "$name overrides the shared file $shared"
  done < <(cd common && find . -type f | sed 's|^\./||')
  grep -q "\`$name\`" README.md || fail "README.md does not mention the $name template"
done

if [ "$problems" -gt 0 ]; then
  echo "contract: $problems problem(s)" >&2
  exit 1
fi
echo "contract: ${#names[@]} templates satisfy the stack contract"
