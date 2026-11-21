#!/usr/bin/env bash
set -uo pipefail
trap 'echo "protect-paths: internal error; blocking" >&2; exit 2' ERR
command -v jq >/dev/null 2>&1 || { echo "protect-paths: jq missing; blocking" >&2; exit 2; }
input=$(cat)
f=$(printf '%s' "$input" | jq -er '(.tool_input.file_path // .tool_input.notebook_path) | select(type == "string" and length > 0)') || { echo "protect-paths: no path in hook input; blocking" >&2; exit 2; }
session=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null) || session=""
here=$(cd "$(dirname "$0")" && pwd)
. "$here/events.sh" 2>/dev/null || unslop_event() { :; }
canon() {
  local path=$1 dir rest="" out part parts
  case "$path" in /*) ;; *) path="$PWD/$path" ;; esac
  dir=$path
  while [ ! -d "$dir" ]; do
    rest="/$(basename "$dir")$rest"
    dir=$(dirname "$dir")
  done
  out=$(cd "$dir" && pwd -P)
  IFS=/ read -ra parts <<<"${rest#/}"
  for part in ${parts[@]+"${parts[@]}"}; do
    case "$part" in
      '' | .) ;;
      ..) out=$(dirname "$out") ;;
      *) out="$out/$part" ;;
    esac
  done
  printf '%s\n' "$out"
}
root=$(canon "${CLAUDE_PROJECT_DIR:?}")
home=$(canon "$HOME")
f=$(canon "$f")
block() {
  unslop_event protect-paths "${2:-guardrail file}" "$1" "$root" "$session"
  echo "Blocked: $1 is a guardrail file. Describe the change you need in your final message; a human applies it." >&2
  exit 2
}
case "$f" in
  "$home"/.claude/*|"$home"/.claude.json|*/.git/hooks/*|*/.git/config) block "$f" "claude or git settings" ;;
esac
rel=${f#"$root"/}
case "$rel" in
  .claude/worktrees/*/*)
    tree=${rel#.claude/worktrees/}
    root="$root/.claude/worktrees/${tree%%/*}"
    rel=${f#"$root"/}
    ;;
esac
case "$rel" in
  .claude/agent-memory/*|.claude/agent-memory-local/*) ;;
  .claude/*|.mcp.json) block "$rel" "claude settings" ;;
esac
[ -f "$root/.claude/unslop.json" ] || [ -f "$root/unslop.toml" ] || exit 0
guarded() {
  case "$1" in
    CLAUDE.md|AGENTS.md|.github/*|CODEOWNERS|scripts/*|tools/guard/*|.unslop/*|unslop.toml) block "$rel" ;;
    .npmrc|tsconfig*.json|*/tsconfig*.json|eslint.config.*|.eslintrc*|eslint-rules/*|.dependency-cruiser.*|knip.*|.jscpd.json|stryker.config.*|vitest.config.*|vite.config.*|jest.config.*|.prettierrc*|.prettierignore|playwright.config.*|tailwind.config.*|postcss.config.*|lighthouserc.*|.size-limit.*) block "$rel" ;;
    gradle.properties|gradlew|gradlew.bat|gradle/wrapper/*|build-logic/*|mvnw|.mvn/*|detekt.yml|config/*) block "$rel" ;;
    setup.cfg|ruff.toml|.ruff.toml|pyrightconfig.json|mypy.ini|pytest.ini|tox.ini|.coveragerc|.importlinter|lefthook.yml) block "$rel" ;;
    .python-version|.node-version|.nvmrc|.java-version|.sdkmanrc|.tool-versions|.editorconfig|.sqlfluff|mise.toml|mise.lock|renovate.json) block "$rel" ;;
    .hadolint.yaml|.gitleaks.toml|.semgrep*|*.rego|Dockerfile|*/Dockerfile|.squawk.toml|atlas.hcl|flyway.toml) block "$rel" ;;
    migrations/*|*/migrations/*|docs/decisions/*) if [ -e "$f" ]; then block "$rel" "existing migration or decision"; fi ;;
  esac
  [ -f "$root/.claude/unslop.json" ] || return 0
  case "$1" in
    package.json|*/package.json|package-lock.json|yarn.lock|pnpm-lock.yaml|pnpm-workspace.yaml|pyproject.toml|*/pyproject.toml|uv.lock|poetry.lock) block "$rel" "dependency file" ;;
    build.gradle|*/build.gradle|build.gradle.kts|*/build.gradle.kts|settings.gradle|settings.gradle.kts|gradle/*|pom.xml|*/pom.xml) block "$rel" "dependency file" ;;
  esac
}
guarded "$rel"
while IFS= read -r stack; do
  case "$stack" in
    ""|.) ;;
    *) case "$rel" in "$stack"/*) guarded "${rel#"$stack"/}" ;; esac ;;
  esac
done < <(sed -n 's/^ *path *= *"\([^"]*\)".*/\1/p' "$root/unslop.toml" 2>/dev/null)
if [ -f "$root/.claude/tests.locked" ]; then
  case "$rel" in
    *.test.*|*.spec.*|*/__snapshots__/*|src/test/*|*/src/test/*|tests/*|*/tests/*|test/*|*/test/*|test_*.py|*/test_*.py|*_test.py) block "$rel (tests are locked for this phase)" "tests locked" ;;
  esac
fi
exit 0
