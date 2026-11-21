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
names=()
while IFS= read -r name; do
  names+=("$name")
done < <(jq -r '.templates[].name' "$catalog")

while IFS= read -r dir; do
  name=$(basename "$dir")
  printf '%s\n' "${names[@]}" | grep -qx -- "$name" || fail "templates/$name is not listed in $catalog"
done < <(find templates -mindepth 1 -maxdepth 1 -type d | sort)

for workflow in .github/workflows/*.yml templates/*/.github/workflows/*.yml; do
  while IFS= read -r ref; do
    [[ "$ref" =~ @[0-9a-f]{40}$ || "$ref" == ./* ]] || fail "$workflow uses an action not pinned to a commit SHA: $ref"
  done < <(sed -n 's/^ *- *uses: *\([^ ]*\).*/\1/p; s/^ *uses: *\([^ ]*\).*/\1/p' "$workflow")
  grep -q 'persist-credentials: false' "$workflow" || fail "$workflow must check out with persist-credentials: false"
  grep -Eq '^permissions:' "$workflow" || fail "$workflow must declare top-level permissions"
done

if grep -rIl -e 'kimkun0504' -e 'Kun Kim' common templates src/unslop/data >/dev/null 2>&1; then
  fail "shared files name a specific owner; use UNSLOP_OWNER_HANDLE and UNSLOP_OWNER_NAME placeholders"
fi
scaffold=$(mktemp -d)
GIT_AUTHOR_NAME=c GIT_AUTHOR_EMAIL=c@c GIT_COMMITTER_NAME=c GIT_COMMITTER_EMAIL=c@c UNSLOP_OWNER=octocat UNSLOP_OWNER_NAME="Mona Lisa" \
  bin/unslop new python "$scaffold/p" >/dev/null
if grep -rIl 'UNSLOP_' "$scaffold/p" --exclude-dir=.git >/dev/null; then fail "unslop new left owner placeholders unfilled"; fi
grep -q '^\* @octocat$' "$scaffold/p/.github/CODEOWNERS" || fail "unslop new did not fill CODEOWNERS"
rm -rf "$scaffold"

expected=$(tests/contract/stacks-table.sh)
actual=$(sed -n '/<!-- stacks:start -->/,/<!-- stacks:end -->/p' README.md | sed '1d;$d')
[ "$expected" = "$actual" ] || fail "README.md stacks tables are out of date; regenerate them with tests/contract/stacks-table.sh"

while IFS= read -r ref; do
  [[ "$ref" =~ @[0-9a-f]{40}$ ]] || fail "action.yml uses an action not pinned to a commit SHA: $ref"
done < <(sed -n 's/^ *- *uses: *\([^ ]*\).*/\1/p; s/^ *uses: *\([^ ]*\).*/\1/p' action.yml)

profiles=$(python3 -c 'import ast, pathlib
tree = ast.parse(pathlib.Path("src/unslop/profiles.py").read_text())
found = [n for n in tree.body if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "PROFILES"]
print("\n".join(sorted(key.value for key in found[0].value.keys)))')
[ -n "$profiles" ] || fail "could not read PROFILES from src/unslop/profiles.py"
while IFS= read -r profile; do
  printf '%s\n' "$profiles" | grep -qx -- "$profile" || fail "catalog names profile $profile but src/unslop/profiles.py has no such profile"
done < <(jq -r '(.adopt[].name), (.templates[].adopt // empty)' "$catalog" | sort -u)
while IFS= read -r profile; do
  jq -e --arg p "$profile" 'any(.adopt[]; .name == $p)' "$catalog" >/dev/null || fail "profile $profile is not listed in the catalog adopt section"
  [ -f "tests/adopt/$profile.sh" ] || compgen -G "tests/adopt/$profile-*.sh" >/dev/null || fail "profile $profile has no fixture in tests/adopt"
done <<<"$profiles"

cmp -s templates/kotlin-spring/tools/guard/kotlin_guard.py src/unslop/data/jvm/guard/kotlin_guard.py || fail "src/unslop/data/jvm/guard/kotlin_guard.py differs from the kotlin-spring template's copy"

version=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' src/unslop/__init__.py)
[ "$(jq -r .version plugin/.claude-plugin/plugin.json)" = "$version" ] || fail "plugin.json version differs from the package version $version"

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
