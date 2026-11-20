#!/usr/bin/env bash
set -uo pipefail
trap 'echo "guard-bash: internal error; blocking" >&2; exit 2' ERR
command -v jq >/dev/null 2>&1 || { echo "guard-bash: jq missing; blocking" >&2; exit 2; }
input=$(cat)
raw=$(printf '%s' "$input" | jq -er '.tool_input.command | select(type == "string" and length > 0)') || { echo "guard-bash: no command in hook input; blocking" >&2; exit 2; }
raw=$(printf '%s' "$raw" | tr -s '[:space:]' ' ')
if printf '%s' "$raw" | grep -Eq -- '(^|[ ;&|(])(ba|z|da)?sh -c|eval |node (-e|--eval|-p)|python3? -c|base64 (-d|--decode)|\$\(|`'; then
  cmd=$raw
else
  cmd=$(printf '%s' "$raw" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g")
fi
deny() { echo "Blocked by guard-bash (tripwire): $1. Fix the underlying problem or ask the human." >&2; exit 2; }
has() { printf '%s' "$cmd" | grep -Eq -- "$1"; }
has '--no-verify|(^|[ ;&|])(HUSKY|LEFTHOOK|SKIP)=|core\.hooksPath' && deny "git hook bypass"
has 'git( -[cC] [^ ]+)* commit( [^;&|]*)? -[a-zA-Z]*n[a-zA-Z]*( |$|[);&|])' && deny "git commit -n skips hooks"
has 'git( -[cC] [^ ]+)* push( [^;&|]*)? (--force|-f( |$|[);&|])|--force-with-lease|\+[^ ]+)' && deny "force push"
has '(curl|wget)[^;&]*\| *(sudo )?(ba|z|da)?sh|(ba|z)?sh <\( *(curl|wget)|base64 (-d|--decode)[^;&]*\| *(ba|z)?sh' && deny "download-and-execute"
has 'git( -[cC] [^ ]+)* (reset --hard|clean -[a-zA-Z]*f|checkout -- \.|restore( --[a-z]+)* \.|stash (drop|clear)|branch -D|update-ref -d)' && deny "destructive git"
has 'rm -[a-zA-Z]*r[a-zA-Z]* +(-[a-zA-Z]+ +)*(/|~(/[^ ]*)?|[$]HOME[^ ]*|\.\./[^ ]*)( |$|[);&|])' && deny "recursive delete outside the project"
has '(terraform|tofu) +(apply|destroy|import|force-unlock|state +(rm|mv|push))|-auto-approve' && deny "infrastructure mutation; the agent may only plan"
has 'kubectl +(apply|create|delete|edit|patch|replace|scale|rollout)|helm +(install|upgrade|uninstall|rollback)|argocd +app +(sync|delete)' && deny "cluster mutation; Argo CD deploys from Git"
has 'prisma +(migrate +reset|db +push)|drizzle-kit +push|flyway +clean|atlas +schema +apply|PRISMA_USER_CONSENT' && deny "destructive or unreviewed schema change"
printf '%s' "$raw" | grep -Eiq -- '(drop +(table|schema|database)|truncate +table)' && deny "destructive SQL"
has 'minimum.?release.?age|exclude-newer' && deny "release-age gate change"
has '(^|[ /=<])\.env(\.[A-Za-z0-9_-]+)?( |$|;|\|)' && ! has '\.env\.example' && deny "reading or writing .env secrets"
worktree_root() {
  local cwd top
  cwd=$(printf '%s' "$1" | jq -r '.cwd // empty' 2>/dev/null) || cwd=""
  [ -n "$cwd" ] && [ -d "$cwd" ] || return 0
  top=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || top=""
  if [ -n "$top" ] && { [ -f "$top/unslop.toml" ] || [ -f "$top/.claude/unslop.json" ]; }; then
    printf '%s\n' "$top"
  fi
}
root=$(worktree_root "$input")
[ -n "$root" ] || root=${CLAUDE_PROJECT_DIR:-}
if [ -n "$root" ] && { [ -f "$root/unslop.toml" ] || [ -f "$root/.claude/unslop.json" ]; }; then
  has '(^|[ ;&|(/])unslop +(baseline|init|upgrade)( |$|[);&|])|scripts/rebaseline' && deny "only a human records the baseline or changes the unslop setup"
  has 'claude +plugins? +(disable|uninstall|remove)|plugins? +marketplace +remove' && deny "the unslop plugin stays enabled in this repository"
fi
exit 0
