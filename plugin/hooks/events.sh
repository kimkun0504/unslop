#!/usr/bin/env bash
unslop_event() {
  local dir="${XDG_STATE_HOME:-$HOME/.local/state}/unslop"
  mkdir -p "$dir" 2>/dev/null || return 0
  jq -nc --arg hook "$1" --arg rule "$2" --arg detail "${3:-}" --arg repo "${4:-}" --arg session "${5:-}" \
    '{time: (now | floor), hook: $hook, rule: $rule, detail: $detail, repo: $repo, session: $session}' \
    >>"$dir/events.jsonl" 2>/dev/null || true
}
