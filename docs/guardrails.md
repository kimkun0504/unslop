# Guardrail catalog

Every guardrail in unslop, grouped by where it runs. Each one is enforced by a tool, not by instructions. The **Strength** column says how hard it is to get around:

- **Boundary**: enforced by the operating system or GitHub. Claude cannot get around it from inside a session.
- **Gate**: a check that must pass. Claude can only satisfy it by doing the work.
- **Tripwire**: pattern matching that stops the ordinary case. A determined workaround can get past it, so a boundary or gate backs it up.

## 1. Machine layer

Installed by `sudo ./install/install.sh system`. Applies to every repository on the machine. Files: `global/managed-settings.json` and `global/hooks/`, installed root-owned so Claude cannot edit them.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| M1 | Secrets cannot be read: `.env*`, `~/.ssh`, `~/.aws`, `~/.kube`, gcloud, Docker, npm, PyPI and netrc credentials, `*.pem`, `*.key` | `permissions.deny` Read rules plus `sandbox.filesystem.denyRead` | Boundary for shell, tripwire for the Read tool |
| M2 | Credential environment variables are hidden from shell commands: `GITHUB_TOKEN`, `GH_TOKEN`, `NPM_TOKEN`, AWS keys, `DATABASE_URL`, `PGPASSWORD` | `sandbox.credentials.envVars` deny | Boundary |
| M3 | Shell commands run sandboxed, may write only to the project and package caches, and may reach only package registries and GitHub | `sandbox` with `failIfUnavailable`, `allowUnsandboxedCommands: false`, `network.strictAllowlist` | Boundary |
| M4 | Claude's own configuration cannot be changed: `~/.claude`, `.claude/`, `.mcp.json`, git hooks and git config | Edit deny rules, sandbox `denyWrite`, `protect-paths.sh` | Boundary |
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

Switched on by `.claude/unslop.json`, which every template project contains. Files: `common/` and `templates/<stack>/`.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| P1 | Guardrail files are read-only for Claude: build files, lockfiles, lint and type configs, `scripts/`, CI, `CLAUDE.md`, decision records, Dockerfiles | Project deny rules, sandbox `denyWrite`, `protect-paths.sh` | Boundary |
| P2 | Applied migrations cannot be edited; new ones can be added | `protect-paths.sh` | Gate |
| P3 | Tests can be locked for an implementation phase: `touch .claude/tests.locked` | `protect-paths.sh` | Gate |
| P4 | Claude cannot stop while `scripts/fast-check` fails | Stop hook `stop-gate.sh` | Gate |
| P5 | The stop check never fails silently: three identical failures or twenty in a session end the session with a visible reason | `stop-gate.sh` | Gate |
| P6 | Committed work is still checked; only an exact state that already passed is skipped | `stop-gate.sh` fingerprint of HEAD, diff and untracked files | Gate |
| P7 | No code comments in any language | `scripts/check-comments` (tree-sitter parsers for 300+ languages) | Gate |
| P8 | No new suppressions or skipped tests: `eslint-disable`, `@ts-expect-error`, `# noqa`, `# type: ignore`, `//nolint`, `@Suppress`, `.skip`, `.only`, `@Disabled`, `t.Skip` and more | `scripts/check-diff` | Gate |
| P9 | Existing tests cannot be changed or deleted without the `tests-reviewed` label | `scripts/check-diff` | Gate |
| P10 | Per-stack quality gates: format, lint, types, architecture, tests, coverage, mutation, dead code, supply chain | `scripts/fast-check`, `scripts/verify`, `scripts/mutation`; see the [stack matrix](../README.md#stacks) | Gate |

## 3. CI and GitHub layer

Files: `.github/workflows/ci.yml` and `.github/rulesets/main.json` in each project.

| ID | Guardrail | Mechanism | Strength |
|---|---|---|---|
| G1 | Every change to `main` goes through a pull request | Ruleset `pull_request` | Boundary |
| G2 | No force pushes or branch deletion on `main`, linear history | Ruleset `non_fast_forward`, `deletion`, `required_linear_history` | Boundary |
| G3 | The `verify` job must pass on the latest commit | Ruleset `required_status_checks` with strict policy | Boundary |
| G4 | CI runs the same scripts as local checks, plus mutation testing and vulnerability audit | `ci.yml` | Gate |
| G5 | Actions pinned to commit SHAs, read-only token, credentials not persisted | `ci.yml`, enforced in this repo by the contract check | Gate |
| G6 | Guardrail paths have an owner | `CODEOWNERS` | Boundary when reviews are required |

## 4. Claude profile layer

Installed by `./install/install.sh user`. These guide rather than enforce; everything that matters is enforced by the layers above.

| ID | Item | Purpose |
|---|---|---|
| C1 | `~/.claude/CLAUDE.md` | Ten lines on what tools cannot check: ask before guessing, copy the nearest pattern, test first, never weaken a check, what "done" means |
| C2 | `reviewer` agent | Fresh-context, read-only review against the spec and the decision records, using the rubric in decision record 0003 ([standards §10](standards.md#10-review-rubric)). Ends with `VERDICT: PASS` or `VERDICT: BLOCK`. |
| C3 | `/unslop-spec` | Interviews you into `SPEC.md` with numbered, testable acceptance criteria before code |
| C4 | `/unslop-long-run` | Sets up `feature_list.json`, `progress.md` and a `/goal` exit condition for multi-hour runs |
| C5 | `/unslop-migration` | Safe Postgres migration procedure |

## How the layers back each other up

| If Claude tries to… | First stop | Backstop |
|---|---|---|
| Edit the lint config to make an error go away | P1 deny rule and hook | G1 and G3: the change needs a reviewed PR and passing CI |
| Replace `scripts/fast-check` with `exit 0` | P1 sandbox `denyWrite` | G4: CI runs its own checkout |
| Weaken an assertion | P9 `check-diff` | G3 |
| Write a comment, then stop | P7 in `fast-check` | P4 stop check, then G3 |
| Push straight to `main` | M8 tripwire | G1 and G2 |
| Read a token and call an API with it | M1 and M2 | M3 network allowlist |
| Run `terraform destroy` | M11 tripwire | M2: no cloud credentials in the sandbox |
