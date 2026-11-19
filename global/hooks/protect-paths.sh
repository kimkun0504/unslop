#!/usr/bin/env bash
set -uo pipefail
trap 'echo "protect-paths: internal error; blocking" >&2; exit 2' ERR
command -v jq >/dev/null 2>&1 || { echo "protect-paths: jq missing; blocking" >&2; exit 2; }
f=$(jq -er '(.tool_input.file_path // .tool_input.notebook_path) | select(type == "string" and length > 0)') || { echo "protect-paths: no path in hook input; blocking" >&2; exit 2; }
root="${CLAUDE_PROJECT_DIR:?}"
block() { echo "Blocked: $1 is a guardrail file. Describe the change you need in your final message; a human applies it." >&2; exit 2; }
case "$f" in
  "$HOME"/.claude/*|"$HOME"/.claude.json|*/.git/hooks/*|*/.git/config) block "$f" ;;
esac
rel=${f#"$root"/}
case "$rel" in
  .claude/*|.mcp.json) block "$rel" ;;
esac
[ -f "$root/.claude/unslop.json" ] || exit 0
case "$rel" in
  CLAUDE.md|AGENTS.md|.github/*|CODEOWNERS|scripts/*|tools/guard/*|docs/decisions/*) block "$rel" ;;
  package.json|*/package.json|pnpm-lock.yaml|pnpm-workspace.yaml|.npmrc|tsconfig*.json|*/tsconfig*.json|eslint.config.*|eslint-rules/*|.dependency-cruiser.*|knip.*|stryker.config.*|vitest.config.*|vite.config.*|.prettierrc*|.prettierignore|playwright.config.*|lighthouserc.*|.size-limit.*) block "$rel" ;;
  build.gradle.kts|*/build.gradle.kts|settings.gradle.kts|gradle/*|build-logic/*|gradle.properties|gradlew|gradlew.bat|config/*) block "$rel" ;;
  go.mod|go.sum|*/go.mod|*/go.sum|.golangci.y*ml|.custom-gcl.yml|.go-arch-lint.yml) block "$rel" ;;
  pyproject.toml|*/pyproject.toml|uv.lock|.importlinter|ruff.toml|.python-version|lefthook.yml) block "$rel" ;;
  versions.tf|*/versions.tf|.tflint.hcl|.checkov.yaml|.terraform.lock.hcl) block "$rel" ;;
  mise.toml|mise.lock|renovate.json|.hadolint.yaml|.gitleaks.toml|.semgrep*|*.rego|Dockerfile|*/Dockerfile|.squawk.toml|atlas.hcl|flyway.toml) block "$rel" ;;
  migrations/*|*/migrations/*) [ -e "$f" ] && block "$rel" ;;
esac
if [ -f "$root/.claude/tests.locked" ]; then
  case "$rel" in
    *.test.ts|*.test.tsx|*.spec.ts|*.spec.tsx|*/__snapshots__/*|src/test/*|*/src/test/*|*_test.go|tests/*|*/tests/*|test_*.py|*/test_*.py|*_test.py) block "$rel (tests are locked for this phase)" ;;
  esac
fi
exit 0
