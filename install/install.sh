#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix="${UNSLOP_TEST_PREFIX:-}"
hook_dir="$prefix/usr/local/lib/claude-guard"

managed_dir() {
  case "$(uname -s)" in
    Darwin) echo "$prefix/Library/Application Support/ClaudeCode" ;;
    Linux) echo "$prefix/etc/claude-code" ;;
    *) echo "unsupported OS: $(uname -s)" >&2; exit 1 ;;
  esac
}

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing required tool: $1 ($2)" >&2; exit 1; }
}

install_system() {
  [ -n "$prefix" ] || [ "$(id -u)" = 0 ] || { echo "system install needs root: sudo $0 system" >&2; exit 1; }
  require jq "macOS 15+ ships /usr/bin/jq; otherwise: brew install jq"
  require git "xcode-select --install"
  command -v timeout >/dev/null 2>&1 || command -v gtimeout >/dev/null 2>&1 || require perl "needed for the stop gate time limit"
  local dir
  dir=$(managed_dir)
  install -d -m 755 "$hook_dir" "$dir"
  for h in guard-bash.sh protect-paths.sh stop-gate.sh; do
    install -m 755 "$repo/global/hooks/$h" "$hook_dir/$h"
  done
  if [ -f "$dir/managed-settings.json" ] && ! cmp -s "$dir/managed-settings.json" "$repo/global/managed-settings.json"; then
    cp "$dir/managed-settings.json" "$dir/managed-settings.json.bak.$(date +%Y%m%d%H%M%S)"
    echo "backed up existing managed settings in $dir"
  fi
  install -m 644 "$repo/global/managed-settings.json" "$dir/managed-settings.json"
  echo "installed hooks to $hook_dir and managed settings to $dir"
}

install_user() {
  [ -n "$prefix" ] || [ "$(id -u)" != 0 ] || { echo "run the user install without sudo" >&2; exit 1; }
  local home_claude="$HOME/.claude"
  mkdir -p "$home_claude/agents" "$home_claude/skills"
  if [ -f "$home_claude/CLAUDE.md" ] && ! cmp -s "$home_claude/CLAUDE.md" "$repo/global/user/CLAUDE.md"; then
    cp "$home_claude/CLAUDE.md" "$home_claude/CLAUDE.md.bak.$(date +%Y%m%d%H%M%S)"
    echo "backed up existing ~/.claude/CLAUDE.md"
  fi
  cp "$repo/global/user/CLAUDE.md" "$home_claude/CLAUDE.md"
  cp "$repo/global/user/agents/reviewer.md" "$home_claude/agents/reviewer.md"
  for s in "$repo"/global/user/skills/*/; do
    name=$(basename "$s")
    mkdir -p "$home_claude/skills/$name"
    cp "$s"SKILL.md "$home_claude/skills/$name/SKILL.md"
  done
  echo "installed ~/.claude/CLAUDE.md, the reviewer agent and unslop skills"
}

latest_backup() {
  find "$(dirname "$1")" -maxdepth 1 -name "$(basename "$1").bak.*" 2>/dev/null | sort | tail -n 1
}

restore_or_remove() {
  local target=$1 ours=$2 backup
  [ -e "$target" ] || return 0
  if ! cmp -s "$target" "$ours"; then
    echo "kept $target: it differs from what unslop installed, so it was changed by someone else"
    return 0
  fi
  backup=$(latest_backup "$target")
  if [ -n "$backup" ]; then
    mv "$backup" "$target"
    echo "restored $target from $backup"
  else
    rm -f "$target"
    echo "removed $target"
  fi
}

uninstall_system() {
  [ -n "$prefix" ] || [ "$(id -u)" = 0 ] || { echo "system uninstall needs root: sudo $0 uninstall-system" >&2; exit 1; }
  local dir h
  dir=$(managed_dir)
  for h in guard-bash.sh protect-paths.sh stop-gate.sh; do
    if [ -f "$hook_dir/$h" ]; then
      rm -f "$hook_dir/$h"
      echo "removed $hook_dir/$h"
    fi
  done
  rmdir "$hook_dir" 2>/dev/null || true
  restore_or_remove "$dir/managed-settings.json" "$repo/global/managed-settings.json"
  echo "machine layer removed; Claude Code picks this up in new sessions"
}

uninstall_user() {
  [ -n "$prefix" ] || [ "$(id -u)" != 0 ] || { echo "run the user uninstall without sudo" >&2; exit 1; }
  local home_claude="$HOME/.claude" s name
  restore_or_remove "$home_claude/CLAUDE.md" "$repo/global/user/CLAUDE.md"
  if [ -f "$home_claude/agents/reviewer.md" ] && cmp -s "$home_claude/agents/reviewer.md" "$repo/global/user/agents/reviewer.md"; then
    rm -f "$home_claude/agents/reviewer.md"
    echo "removed the reviewer agent"
  fi
  for s in "$repo"/global/user/skills/*/; do
    name=$(basename "$s")
    if [ -f "$home_claude/skills/$name/SKILL.md" ] && cmp -s "$home_claude/skills/$name/SKILL.md" "$s"SKILL.md; then
      rm -f "$home_claude/skills/$name/SKILL.md"
      rmdir "$home_claude/skills/$name" 2>/dev/null || true
      echo "removed the $name skill"
    fi
  done
  echo "profile layer removed"
}

check() {
  local dir ok=0
  dir=$(managed_dir)
  for h in guard-bash.sh protect-paths.sh stop-gate.sh; do
    if cmp -s "$repo/global/hooks/$h" "$hook_dir/$h"; then echo "ok   hook $h"; else echo "DIFF hook $h"; ok=1; fi
  done
  if cmp -s "$repo/global/managed-settings.json" "$dir/managed-settings.json"; then echo "ok   managed settings"; else echo "DIFF managed settings"; ok=1; fi
  if cmp -s "$repo/global/user/CLAUDE.md" "$HOME/.claude/CLAUDE.md"; then echo "ok   user CLAUDE.md"; else echo "DIFF user CLAUDE.md"; ok=1; fi
  if [ -f "$HOME/.claude/agents/reviewer.md" ]; then echo "ok   reviewer agent"; else echo "MISS reviewer agent"; ok=1; fi
  return "$ok"
}

case "${1:-}" in
  system) install_system ;;
  user) install_user ;;
  check) check ;;
  uninstall-system) uninstall_system ;;
  uninstall-user) uninstall_user ;;
  *) echo "usage: sudo $0 system | $0 user | $0 check | sudo $0 uninstall-system | $0 uninstall-user" >&2; exit 1 ;;
esac
