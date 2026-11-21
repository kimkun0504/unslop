# Guardrail catalog

Every guardrail in unslop, grouped by where it runs. Each one is enforced by a tool, not by instructions. The **Strength** column says how hard it is to get around:

- **Boundary**: enforced by the operating system or GitHub. Claude cannot get around it from inside a session.
- **Gate**: a check that must pass. Claude can only satisfy it by doing the work.
- **Tripwire**: pattern matching that stops the ordinary case. A determined workaround can get past it, so a boundary or gate backs it up.

## 1. Machine layer

Optional. Installed by `sudo ./install/install.sh system`. Applies to every repository on the machine. Files: `global/managed-settings.json` and the hooks from `plugin/hooks/`, installed root-owned so Claude cannot edit them. With it installed, the project layer's hooks also run from managed settings, so nobody can switch them off from inside a session. `sudo ./install/install.sh uninstall-system` removes them and restores the managed settings file they replaced.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| M1 | Secrets cannot be read: `.env*`, `~/.ssh`, `~/.aws`, `~/.kube`, gcloud, Docker, npm, PyPI and netrc credentials, `*.pem`, `*.key` | `permissions.deny` Read rules plus `sandbox.filesystem.denyRead` | Boundary for shell, tripwire for the Read tool |
| M2 | Credential environment variables are hidden from shell commands: `GITHUB_TOKEN`, `GH_TOKEN`, `NPM_TOKEN`, AWS keys, `DATABASE_URL`, `PGPASSWORD` | `sandbox.credentials.envVars` deny | Boundary |
| M3 | Shell commands run sandboxed, may write only to the project and the toolchain caches of every template stack, and may reach only those stacks' package registries and GitHub | `sandbox` with `failIfUnavailable`, `allowUnsandboxedCommands: false`, `network.strictAllowlist` | Boundary |
| M4 | Claude's own configuration cannot be changed: `~/.claude`, the settings, rules, skills, commands, agents and hooks in `.claude/`, `.mcp.json`, git hooks and git config. Worktrees that Claude Code creates in `.claude/worktrees/` stay editable, with the same rules applied inside each one | Edit deny rules, sandbox `denyWrite`, `protect-paths.sh` | Boundary |
| M5 | No bypass mode | `disableBypassPermissionsMode: "disable"` | Boundary |
| M6 | Project MCP servers are not auto-enabled | `enableAllProjectMcpServers: false` | Boundary |
| M7 | Hook bypasses blocked: `--no-verify`, `commit -n`, `HUSKY=0`, `core.hooksPath` | `guard-bash.sh` | Tripwire |
| M8 | History cannot be rewritten: force pushes, `reset --hard`, `clean -f`, `branch -D`, `stash drop` | `guard-bash.sh` plus deny rules | Tripwire, backed by ruleset G2 |
| M9 | Download-and-execute blocked: `curl … \| sh`, `bash <(curl …)` | `guard-bash.sh` | Tripwire, backed by M3 |
| M10 | Recursive deletes outside the project blocked | `guard-bash.sh` | Tripwire, backed by M3 |
| M11 | Infrastructure and clusters are plan-only: no `terraform apply/destroy/import/state rm`, `kubectl apply/delete/edit/patch/scale`, `helm install/upgrade/uninstall`, `argocd app sync` | `guard-bash.sh` plus deny rules | Tripwire, backed by M2 |
| M12 | Destructive database commands blocked: `DROP TABLE/SCHEMA/DATABASE`, `TRUNCATE TABLE`, `prisma migrate reset`, `flyway clean`, `drizzle-kit push`, `atlas schema apply` | `guard-bash.sh` | Tripwire, backed by M2 |
| M13 | Supply-chain delays cannot be switched off: release-age settings are untouchable | `guard-bash.sh` | Tripwire |
| M14 | Every hook fails closed: missing `jq`, malformed input or an internal error blocks the action | `trap … exit 2` in each hook, `onFailure: "block"` | Gate |

## 2. Project layer

Switched on by `unslop.toml` in a repository set up with `unslop init`, or by `.claude/unslop.json`, which every template project contains. The hooks come from the unslop Claude Code plugin, which the repository's `.claude/settings.json` turns on, and from the machine layer when it is installed. Files: `plugin/`, `common/` and `templates/<stack>/`.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| P1 | Guardrail files are read-only for Claude: lint and type configs, build files and lockfiles in template projects, `scripts/`, CI, `CLAUDE.md`, Dockerfiles | Project deny rules, sandbox `denyWrite`, `protect-paths.sh` | Boundary |
| P2 | Applied migrations and existing decision records cannot be edited; new ones can be added | `protect-paths.sh` | Gate |
| P3 | Tests can be locked for an implementation phase: `touch .claude/tests.locked` | `protect-paths.sh` | Gate |
| P4 | Claude cannot stop while `unslop check --fast`, or `scripts/fast-check` in a template project, fails. A turn that changed nothing since the last check, such as answering a question, is not checked again | Stop hook `stop-gate.sh`, using `stop_hook_active` | Gate |
| P5 | The stop check never fails silently: three identical failures, twenty in a session, or running past the project's time budget end the session with a visible reason | `stop-gate.sh` | Gate |
| P5a | The time budget is per project: `fast_check_seconds` in `unslop.toml` or `.claude/unslop.json`, 240 by default, at most 1700; `unslop init` sets it to twice the measured run plus a minute. The file is read-only for Claude | `stop-gate.sh`, `protect-paths.sh` | Boundary |
| P6 | Committed work is still checked; only an exact state that already passed is skipped | `stop-gate.sh` fingerprint of HEAD, diff and untracked files | Gate |
| P7 | No code comments in any language | `scripts/check-comments` (tree-sitter parsers for 300+ languages) | Gate |
| P8 | No new suppressions or skipped tests: `eslint-disable`, `@ts-expect-error`, `# noqa`, `# type: ignore`, `@Suppress`, `.skip`, `.only`, `@Disabled`, `pytest.mark.skip` and more | `scripts/check-diff` | Gate |
| P9 | Existing tests cannot be changed, deleted or renamed without the `tests-reviewed` label, in every template's test layout. New tests may be appended to the end of an existing test file, with any imports they need | `scripts/check-diff` | Gate |
| P10 | Per-stack quality gates: format, lint, types, architecture, tests, coverage, mutation, dead code, supply chain | `scripts/fast-check`, `scripts/verify`, `scripts/mutation`; see the [stack matrix](../README.md#stacks) | Gate |
| P11 | Claude cannot record a new baseline or switch the plugin off in an unslop repository | `guard-bash.sh` | Tripwire, backed by A5 and the `unslop-reviewed` label |
| P12 | Every block is logged on the computer, per repository, rule and session, so the noisy rules can be found | `events.sh` in each hook, `unslop stats` | Not a guardrail |

## 2a. Adopted repositories

`unslop init` switches the project layer on in an existing repository by adding `unslop.toml`, `.unslop/baseline.json`, `.claude/settings.json` and `.github/workflows/unslop.yml`. P1 to P6, P9, P11 and P12 apply, except that dependency files are not read-only (A8). The rest are rewritten as ratchets inside `unslop check`, so legacy code keeps working and new work meets the full bar. Code: `src/unslop/`.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| A1 | No comments on lines a change adds, unless `comments = "allow"` | `comments.py`, tree-sitter over the lines added since the base | Gate |
| A2 | No lint, type, dead-code or SQL finding beyond the recorded baseline, counted per file and rule so moved code does not count as new; a failure lists the findings on lines the change touches first | `ratchet.py` over SARIF, pyright, ESLint, tsc, vulture, knip and sqlfluff reports | Gate |
| A3 | A file that was formatted stays formatted, and new files must be formatted; legacy files are never forced into a reformat | Format ratchet comparing each changed file before and after | Gate |
| A4 | Every changed line is covered by a test, or the share set by `coverage` | `diff-cover --fail-under` on the project's own coverage report, in CI | Gate |
| A5 | `unslop.toml` and the baseline are read-only for Claude. Changing the configuration or growing the baseline fails the check unless the pull request has the `unslop-reviewed` label | Deny rules, sandbox `denyWrite`, `protect-paths.sh`, and the configuration gate in `unslop check` | Boundary, backed by a gate |
| A6 | Downloaded tools are pinned by checksum | `unslop fetch` | Gate |
| A7 | The unslop version is pinned, and the check refuses to run against a different version | `unslop.toml`, the marketplace `ref`, the action SHA | Gate |
| A8 | Claude may add or update dependencies, and the pull request then needs the `unslop-reviewed` label. In `package.json` and `pyproject.toml`, anything outside the dependency sections fails even locally. In CI, a change to any protected file needs the same label | `guards.py` | Gate |
| A9 | No new copy-pasted code: a block of 50 tokens or more, outside tests, that is not on the base branch | jscpd with `--baseline-from-ref` | Gate |
| A10 | Large changes are flagged: a warning above `diff_warn_lines`, a failure above `diff_max_lines` when it is set | `slop.py` | Gate when a limit is set |
| A11 | Optional: every mutant on a changed line must be killed, for Python and TypeScript | mutmut or Stryker limited to changed lines, when `mutation = true` | Gate |

## 3. CI and GitHub layer

Files: `.github/workflows/ci.yml` and `.github/rulesets/main.json` in each template project; `.github/workflows/unslop.yml`, which runs the unslop action, in an adopted repository. `unslop ruleset --apply` applies the ruleset, requiring `verify` in a template project and `unslop` in an adopted one.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| G1 | Every change to `main` goes through a pull request | Ruleset `pull_request` | Boundary |
| G2 | No force pushes or branch deletion on `main`, linear history | Ruleset `non_fast_forward`, `deletion`, `required_linear_history` | Boundary |
| G3 | The `verify` job must pass on the latest commit | Ruleset `required_status_checks` with strict policy | Boundary |
| G4 | CI runs the same scripts as local checks, plus mutation testing and vulnerability audit | `ci.yml` | Gate |
| G5 | Actions pinned to commit SHAs, read-only token, credentials not persisted | `ci.yml`, enforced in this repo by the contract check | Gate |
| G6 | Guardrail paths have an owner | `CODEOWNERS` | Boundary when reviews are required |

## 4. Claude profile and plugin extras

These guide rather than enforce; everything that matters is enforced by the layers above. C1 is optional, installed by `./install/install.sh user` and removed by `./install/install.sh uninstall-user`. C2 to C5 come with the plugin.

| ID | Item | Purpose |
|---|---|---|
| C1 | `~/.claude/CLAUDE.md` | Ten lines on what tools cannot check: ask before guessing, copy the nearest pattern, test first, never weaken a check, what "done" means |
| C2 | `reviewer` agent | Fresh-context, read-only review against the spec and the decision records, using the rubric in decision record 0003 ([standards §10](standards.md#10-review-rubric)). Ends with `VERDICT: PASS` or `VERDICT: BLOCK`. |
| C3 | `/unslop:spec` | Interviews you into `SPEC.md` with numbered, testable acceptance criteria before code |
| C4 | `/unslop:long-run` | Sets up `feature_list.json`, `progress.md` and a `/goal` exit condition for multi-hour runs |
| C5 | `/unslop:migration` | Safe Postgres migration procedure |

## How the layers back each other up

| If Claude tries to… | First stop | Backstop |
|---|---|---|
| Edit the lint config to make an error go away | P1 deny rule and hook | G1 and G3: the change needs a reviewed PR and passing CI |
| Replace `scripts/fast-check` with `exit 0` | P1 sandbox `denyWrite` | G4: CI runs its own checkout |
| Weaken an assertion | P9 `check-diff` | G3 |
| Grow the baseline to hide a new finding | A5 deny rules, P11 tripwire | A5 configuration gate, then G3 |
| Add a dependency, or slip a test setting into `pyproject.toml` | A8: the dependency section is fine, anything else fails | The `unslop-reviewed` label in CI, then G3 |
| Paste a function instead of extracting it | A9 in the fast check | P4 stop check, then G3 |
| Write a comment, then stop | P7 in `fast-check` | P4 stop check, then G3 |
| Push straight to `main` | M8 tripwire | G1 and G2 |
| Read a token and call an API with it | M1 and M2 | M3 network allowlist |
| Run `terraform destroy` | M11 tripwire | M2: no cloud credentials in the sandbox |
