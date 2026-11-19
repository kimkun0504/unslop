#!/usr/bin/env bash
set -euo pipefail
catalog="$(cd "$(dirname "$0")/../.." && pwd)/templates/catalog.json"
echo "| Template | Format | Lint and types | Architecture | Tests | Mutation | Adopt profile |"
echo "|---|---|---|---|---|---|---|"
jq -r '.templates[] | "| `\(.name)` | \(.summary.format) | \(.summary.lint) | \(.summary.architecture) | \(.summary.tests) | \(.summary.mutation) | \(if .adopt then "`\(.adopt)`" else "not yet" end) |"' "$catalog"
echo
echo "| Adopt profile | For | Format, on changed files | Lint and types, ratcheted | Tests and changed-line coverage |"
echo "|---|---|---|---|---|"
jq -r '.adopt[] | "| `\(.name)` | \(.title): \(.detects) | \(.format) | \(.checks) | \(.tests) |"' "$catalog"
