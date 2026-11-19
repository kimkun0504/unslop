# Adopting an existing repository

Templates start clean. An existing repository has years of findings, so turning on every rule at once would fail on the first run, and Claude could not fix the configuration because it is protected. `unslop adopt` applies the same guardrails as a ratchet: legacy code is recorded as it is, and every new or changed line meets the full bar.

## What changes in the repository

| Path | What it is | Who can change it |
|---|---|---|
| `.unslop/adopt.json` | The commands for formatting, lint and type checks, tests and coverage, written by the profile's detection | A human |
| `.unslop/baseline/*.json` | Findings that existed at adoption, counted per file and rule | A human, with `scripts/rebaseline` |
| `.unslop/config/` | The strict lint and type configuration new code must meet | A human |
| `.unslop/guard/` | The runner, the checksum-pinned tool fetcher and stack guards | A human |
| `.unslop/decisions/` | Decision records 0001 to 0003: no comments, guardrails change only by humans, the review rubric | A human |
| `.unslop/CLAUDE.md` | Rules for Claude, imported from your `CLAUDE.md` with one `@.unslop/CLAUDE.md` line | A human |
| `scripts/fast-check`, `scripts/verify`, `scripts/setup`, `scripts/rebaseline` | The same entry points templates have; the end-of-session check runs `fast-check` | A human |
| `.claude/unslop.json`, `.claude/settings.json` | The marker that switches the project layer on, and deny rules merged into any settings you already have | A human |
| `.github/workflows/unslop.yml`, `.unslop/ruleset.json` | CI job `unslop` and a ruleset that requires it | A human |

Nothing existing is overwritten. If one of these paths is already taken, adoption stops and names it.

## What `fast-check` enforces

| Check | Legacy code | New and changed code |
|---|---|---|
| Comments | Untouched | Forbidden on every added line |
| Suppressions and skipped tests | Untouched | Forbidden on every added line |
| Existing tests | Cannot be edited or deleted without the `tests-reviewed` label | Same |
| Formatting | Never forced | New files must be formatted; a file that was formatted must stay formatted |
| Lint and types | Recorded in the baseline | No count of findings per file and rule may grow |
| Tests | Must pass | Must pass |
| Coverage | Not measured | Every changed line must be covered |

When Claude fixes a recorded finding, the check says so; a human locks the improvement in with `scripts/rebaseline` so the finding cannot come back.

## Steps

1. Install the machine layer if you have not: `sudo ./install/install.sh system` and `./install/install.sh user` from the unslop clone.
2. Pick the profile with `bin/unslop list`, then, on a clean branch of your repository:

   ```bash
   ~/Desktop/unslop/bin/unslop adopt python ~/code/my-service
   ```

   Adoption copies the files, detects your package manager, test runner and coverage tool, records the baseline and runs `fast-check` once. If detection guessed wrong, it stops with the reason: edit the commands in `.unslop/adopt.json`, then run `scripts/setup` and `scripts/rebaseline`.
3. Review `git status`, commit, push and open a pull request. Check the toolchain versions in `.github/workflows/unslop.yml`.
4. After it merges, apply the ruleset so `unslop` is a required check:

   ```bash
   gh api -X POST repos/OWNER/REPO/rulesets --input .unslop/ruleset.json
   ```

## Profiles

The table of profiles, what each detects and which tools it runs is generated from the catalog in the [README](../README.md#stacks). A repository with several stacks can be adopted with one profile; to add a second, append its checks to `.unslop/adopt.json` by hand and run `scripts/rebaseline`.

## Limits

Architecture rules and mutation testing are not adopted, because they depend on a layout the repository may not have. See [Known limits](limits.md) for this and the other gaps.
