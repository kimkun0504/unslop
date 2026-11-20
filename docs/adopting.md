# Adopting an existing repository

Templates start clean. An existing repository has years of findings, so turning on every rule at once would fail on the first run, and Claude could not fix the configuration because it is protected. `unslop init` applies the same guardrails as a ratchet: legacy code is recorded as it is, and every new or changed line meets the full bar.

## Steps

1. On a clean branch of your repository:

   ```bash
   uvx --from git+https://github.com/kimkun0504/unslop@v0.3.0 unslop init
   ```

   `init` finds the stacks from the files it sees: one at the repository root, plus any top-level folder with a different stack, such as a React app in `web/` beside a Python API. To choose yourself, pass `--stack PROFILE[:FOLDER]` once per stack, for example `--stack python --stack typescript:web`. It installs dependencies with `unslop setup`, records the baseline, runs `unslop check` once, and sets the end-of-turn time budget to twice that run plus a minute, between 240 and 1700 seconds.
2. Review `git status`: four new or changed files, listed below. Commit, push and open a pull request.
3. Open Claude Code in the repository and accept the folder trust prompt. The unslop plugin installs from the marketplace named in `.claude/settings.json`; `/plugin` lists it.
4. After the pull request merges, require the check:

   ```bash
   unslop ruleset --apply
   ```

If detection guessed wrong, `init` stops and says why. Override the command in `unslop.toml` (see below), then run `unslop setup` and `unslop baseline`.

## What changes in the repository

| Path | What it is | Who can change it |
|---|---|---|
| `unslop.toml` | The stacks and their folders, the pinned unslop version, the time budget, and any command overrides | A human, with the `unslop-reviewed` label |
| `.unslop/baseline.json` | Findings that existed at adoption, counted per file and rule | A human, with `unslop baseline`; growth needs the `unslop-reviewed` label |
| `.claude/settings.json` | Turns the plugin on and denies Claude edits to the files below. Merged into any settings you already have | A human |
| `.github/workflows/unslop.yml` | The `unslop` CI job | A human |

Reports, generated tool configs and helper scripts go in `.unslop/out/`, which ignores itself in git. Nothing existing is overwritten; `init` stops if `unslop.toml` or the workflow already exists.

`.claude/settings.json` denies Claude edits to `unslop.toml`, `.unslop/`, `.claude/`, `.github/`, `CLAUDE.md`, `AGENTS.md`, and the build files and lockfiles your repository actually has, such as `pyproject.toml`, `package.json` or `go.mod`.

## What `unslop check` enforces

| Check | Legacy code | New and changed code |
|---|---|---|
| Comments | Untouched | Forbidden on every added line |
| Suppressions and skipped tests | Untouched | Forbidden on every added line |
| Existing tests | Cannot be edited or deleted without the `tests-reviewed` label; new tests can be appended to an existing file, with their imports | Same |
| Guardrail configuration | `unslop.toml` changes and baseline growth need the `unslop-reviewed` label | Same |
| Formatting | Never forced | New files must be formatted; a file that was formatted must stay formatted |
| Lint and types | Recorded in the baseline | No count of findings per file and rule may grow; a failure shows which findings sit on the lines you touched |
| Tests | Must pass | Must pass |
| Coverage | Not measured | Every changed line must be covered |

When Claude fixes a recorded finding, the check says so. A human locks the improvement in with `unslop baseline` so the finding cannot come back. The plugin blocks Claude from running `unslop baseline` itself.

## Tuning the commands

`unslop plan` prints the exact commands each gate runs. To change one, add a `[commands]` table to `unslop.toml`:

```toml
version = "0.3.0"
profile = "python"
fast_check_seconds = 300

[commands]
setup = "uv sync --locked --all-extras"
tests = "uv run pytest -q tests/unit --cov=src --cov-report=xml:.unslop/out/coverage.xml"
coverage = ".unslop/out/coverage.xml"
```

`setup`, `tests` and `coverage` can be overridden. With several stacks, put the overrides in a `[stack.commands]` table after the stack they belong to. An empty `coverage` turns changed-line coverage off. Changes to `unslop.toml` need the `unslop-reviewed` label on the pull request.

## Several stacks in one repository

Each stack runs in its own folder with its own tools, and its findings are recorded under its own name in the baseline, such as `web:eslint`. `unslop.toml` lists them:

```toml
version = "0.3.0"
fast_check_seconds = 240

[[stack]]
profile = "python"
path = "."

[[stack]]
profile = "typescript"
path = "web"

[stack.commands]
tests = "npx --no-install vitest run --coverage.enabled --coverage.reporter=cobertura --coverage.reportsDirectory=.unslop/out"
```

The `[stack.commands]` table after a stack overrides that stack's commands. Build files and lockfiles inside each stack's folder, such as `web/package-lock.json`, are protected the same way as the ones at the root. The CI action sets up every toolchain the stacks need.

## Upgrading

Run `upgrade` from the version you want, on a branch:

```bash
uvx --from git+https://github.com/kimkun0504/unslop@v0.3.0 unslop upgrade
```

It moves the three pins together: the version in `unslop.toml`, the plugin's marketplace `ref` in `.claude/settings.json`, and the action in `.github/workflows/unslop.yml`, resolved to the tag's commit. It refuses a version that is not tagged yet. Open the pull request with the `unslop-reviewed` label, since `unslop.toml` changes. After it merges, `/plugin update unslop@unslop` in Claude Code picks up the new plugin.

## When something is off

`unslop doctor` checks that `git`, `uv` and `jq` are installed, that `unslop.toml` is valid, that the three pins agree, that each stack's toolchain is on the PATH, that the baseline is committed, that the plugin is installed at the pinned version, and that the default branch requires the `unslop` check. Each line says what to do. `--offline` skips the checks that need GitHub.

## Profiles

The table of profiles, what each detects and which tools it runs is generated from the catalog in the [README](../README.md#stacks).

## Limits

Architecture rules and mutation testing are not adopted, because they depend on a layout the repository may not have. Two stacks of the same kind need separate folders. See [Known limits](limits.md) for these and the other gaps.
