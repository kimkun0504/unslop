#!/usr/bin/env bash
set -uo pipefail
git config --global user.name ci
git config --global user.email ci@example.com
work="${RUNNER_TEMP:-/tmp}/scratch"
UNSLOP_OWNER=ci bin/unslop new swift "$work"
cd "$work" || exit 0
scripts/setup > /dev/null 2>&1
for i in 1 2 3 4 5 6; do
  echo "=== run $i"
  swift test --quiet --enable-code-coverage 2>&1 | grep -E 'Test run|Executed [1-9]'
  report=$(swift test --show-codecov-path)
  dir=$(dirname "$report")
  ls -la "$dir"
  uv run --quiet --no-project --python 3.13 python tools/guard/coverage.py "$report"
  prof=$(find "$dir" -name '*.profdata' | head -1)
  bins=$(find .build -name '*-test-runner' -o -name '*Tests.so' -o -name '*.xctest' | head -5)
  echo "binaries: $bins"
  for b in $bins; do llvm-cov show "$b" -instr-profile "$prof" Sources/CLI/Application.swift 2>&1 | grep -E '^ +[0-9]+\| +0\|'; done
done
exit 0
