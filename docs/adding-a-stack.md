# Adding a stack

A stack is a folder in `templates/` plus an entry in `templates/catalog.json`. `tests/contract/check.sh` enforces everything marked **must**, and the self-test workflow proves the rest. A stack is not done until all of it passes in CI.

## What a new project gets

`bin/unslop new <stack> <dir>` copies `common/` first, then `templates/<stack>/`. A template must not contain any file that `common/` already provides.

| From `common/` | Purpose |
|---|---|
| `.claude/unslop.json` | Turns on the strict local layer (protected files, end-of-session check) |
| `.claude/settings.json` | Project deny rules and sandbox write protection for guardrail files |
| `.github/CODEOWNERS`, `.github/rulesets/main.json` | Branch protection to apply on GitHub |
| `docs/decisions/` | Decision records 0001 (no comments) and 0002 (guardrails change only by humans), plus a template |
| `scripts/check-comments` | The comment ban for every language |
| `scripts/check-diff` | Rejects new suppressions and skipped tests, and edits to existing tests |
| `tools/guard/no_comments.py` | The parser-based checker behind `check-comments` |
| `SPEC.md`, `feature_list.json`, `progress.md` | Inputs and state for spec-first, long-running work |

## The contract

### Files

| Path | Rule |
|---|---|
| `CLAUDE.md` | **Must** exist, be 25 lines or fewer and name `scripts/fast-check`. It holds only what tools cannot check: layout, commands, the pattern to copy. |
| `.gitignore` | **Must** ignore `.env`. |
| `scripts/setup` | **Must** be executable. Installs locked dependencies and checks the pinned toolchain. |
| `scripts/fast-check` | **Must** be executable and run `scripts/check-comments` and `scripts/check-diff`. Runs every fast gate. The end-of-session check runs it, so it should finish in under four minutes. |
| `scripts/verify` | **Must** be executable and run `scripts/fast-check`. Adds the slow gates: coverage, build, integration tests. |
| `scripts/mutation` | **Must** exist and run in CI when the catalog declares a mutation gate, and **must not** exist when it declares none. |
| `.github/workflows/ci.yml` | **Must** have a job named `verify`, pin every action to a commit SHA, declare top-level `permissions`, check out with `fetch-depth: 0` and `persist-credentials: false`, run `scripts/setup` and `scripts/verify`, and honour the `tests-reviewed` label. |

### Gates

Fill every gate the language supports, using the strictest maintained tool. Record each one in the catalog entry.

| Gate | Requirement |
|---|---|
| format | Formatter check, no diff allowed |
| lint | The strictest rule set, suppression comments banned or ignored |
| types | Strictest compiler or checker mode, warnings as errors |
| comments | Covered by `scripts/check-comments`; add a parser rule if the language has comment-like directives worth banning |
| architecture | Import or module boundary rules that fail the build |
| tests | Unit tests plus property-based or fuzz tests where a library exists |
| coverage | 100% line and branch on application code |
| mutation | Every mutant killed, where a maintained tool exists |
| dead-code | Unused code and dependency detection |
| supply-chain | Lockfile enforced, release-age delay where the package manager supports it, vulnerability audit in CI |

### Example code

The template ships one small feature that shows the house style end to end: input parsed into a domain type at the boundary, pure domain logic, an adapter at the edge, and tests that kill every mutant. Agents copy what they see, so the example is the most important file in the template.

## Proving it

1. Add the template and its catalog entry. Mention it in the README stack table.
2. Add a job to `.github/workflows/self-test.yml` that scaffolds the template with `bin/unslop new` (the `unslop` command run from this checkout), runs `scripts/setup`, `scripts/verify` and `scripts/mutation` (if any), and plants violations: a comment, a suppression, a banned call, a layer violation and a behaviour change. Each must be caught by the check meant to catch it.
3. While iterating, push to a branch named `scratch/<template>`. The `probe` job in `.github/workflows/scratch.yml` takes the template from the branch name, scaffolds it, runs the catalog entry's `autofix` command and prints its changes as a patch, then runs every script and records a `RESULT` line for each without failing, so work in progress sends no failure notifications. Add the toolchain setup step for the new stack to that job.
4. Run `tests/contract/check.sh` locally, open a pull request and merge only when every self-test job is green.

## Adding a profile for existing repositories

A profile brings a stack's checks to an existing repository. It is a function in `src/unslop/profiles.py` that runs inside the repository and returns a plan: the setup command, format commands that read a file on standard input and print it formatted, ratcheted checks with their report format (one of the parsers in `src/unslop/findings.py`), and the test command with its coverage report. Reports go under `.unslop/out/`. Strict tool configuration that never changes goes in `src/unslop/data/<name>/config/`, helper scripts in `src/unslop/data/<name>/guard/`; both are copied into `.unslop/out/` on each run. Configuration that depends on the repository is written by the profile with `write_config`.

Register the function in `PROFILES` and its marker files in `MARKERS`, add the toolchain setup to `action.yml`, add the profile to the `adopt` section of `templates/catalog.json`, and regenerate the README tables with `tests/contract/stacks-table.sh`. Add a case to `tests/package/test_profiles.py`, and a fixture in `tests/adopt/<name>.sh` (or `<name>-<variant>.sh`) with a `build_legacy` function that creates a messy repository and a `cases` function that plants new violations with `expect_fail` and clean work with `expect_pass`. Add the fixture to the `adopt` matrix in `.github/workflows/self-test.yml`.
