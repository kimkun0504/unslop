# unslop

Guardrails that make Claude Code produce code you would have written yourself. Standards live in tools that fail the build, not in prose the model may skip.

| Layer | What it enforces | Where |
|---|---|---|
| Machine-wide | Secret files and credentials unreadable, dangerous commands blocked, sandboxed shell with a network allowlist, end-of-session check | `global/managed-settings.json`, `global/hooks/` |
| Your Claude profile | A short `CLAUDE.md`, a read-only reviewer agent, skills for specs, migrations and long runs | `global/user/` |
| Each project | Lint, types, comment ban, architecture rules, suppression and test-tampering checks, coverage and mutation gates | `templates/<stack>/`, `common/` |
| GitHub | Pull requests and passing checks required on `main`, no force pushes | `.github/rulesets/main.json` in each project |

The local hooks give fast feedback and stop accidents. CI plus the branch ruleset is the gate the agent cannot get around.

## Install on macOS

Requirements: `git`, `jq` (included in macOS 15 and later, otherwise `brew install jq`) and `perl` (included).

```bash
git clone https://github.com/kimkun0504/unslop ~/Desktop/unslop
cd ~/Desktop/unslop
sudo ./install/install.sh system
./install/install.sh user
./install/install.sh check
```

`system` copies the hooks to `/usr/local/lib/claude-guard/` and the policy to `/Library/Application Support/ClaudeCode/managed-settings.json`. Both are owned by root, so Claude cannot change them. `user` installs `~/.claude/CLAUDE.md` (backing up any existing one), the `reviewer` agent and the `unslop-*` skills.

After installing, open Claude Code and run `/sandbox` and `/permissions` to confirm the policy loaded.

## What applies where

Every repository on the machine gets the universal layer: no reading `.env`, SSH, AWS or kube credentials; no editing `.claude/`, `.mcp.json` or git hooks; no force pushes, hook bypasses, `terraform apply`, `kubectl apply`, `helm upgrade` or destructive SQL; shell commands run in the sandbox with a network allowlist.

Projects created from a template also contain `.claude/unslop.json`. Its presence switches on the strict layer: guardrail files (build files, lint and type configs, lockfiles, `scripts/`, CI, decision records) become read-only for Claude, and the end-of-session check runs `scripts/fast-check` before Claude may stop.

## Start a project

```bash
~/Desktop/unslop/bin/unslop new python ~/code/my-app
cd ~/code/my-app
scripts/setup
scripts/verify
```

Templates: `python`, `ts-react`, `go`, `kotlin-spring`. Each has the same scripts:

| Script | Runs | Used by |
|---|---|---|
| `scripts/setup` | Install the locked dependencies and check the toolchain | You, CI |
| `scripts/fast-check` | Format, lint, types, comment ban, architecture, suppression scan, tests | End-of-session check |
| `scripts/verify` | fast-check plus 100% coverage and the build | CI |
| `scripts/mutation` | Mutation testing that must kill every mutant (not in Go) | CI |

Then push to GitHub and apply the ruleset once:

```bash
gh api -X POST repos/OWNER/REPO/rulesets --input .github/rulesets/main.json
```

## Working with Claude in a project

1. Run `/unslop-spec` to turn the idea into `SPEC.md` with numbered acceptance criteria. Nothing gets built until you approve it.
2. For a long unattended build, run `/unslop-long-run`. It sets up `feature_list.json` and `progress.md` and gives you the `/goal` condition to paste. The run ends when every criterion has a passing, reviewed test, not when a clock runs out.
3. To stop Claude editing tests while it implements, run `touch .claude/tests.locked` yourself. Delete the file when you want new tests written.
4. When a check blocks Claude, it explains the change it needs in its final message. You make that change in a reviewed pull request.

If a pull request intentionally changes existing tests, add the `tests-reviewed` label so CI accepts it.

## No comments

Comments fail the build in all four stacks: a custom ESLint rule for TypeScript, a tokenizer check for Python, a `go/parser` check for Go and a tree-sitter check for Kotlin. Suppression comments (`eslint-disable`, `@ts-expect-error`, `# noqa`, `# type: ignore`, `//nolint`, `@Suppress`) are banned by the linters and by `scripts/check-diff`. The only exceptions are toolchain directives such as `//go:build` and `/// <reference>` and generated-code headers. See `common/docs/decisions/0001-no-code-comments.md`.

## Tested

`.github/workflows/self-test.yml` runs on every push: shellcheck, 112 hook test cases, and for each template it scaffolds a fresh project and runs `setup`, `verify` and `mutation`.

Not covered by automated tests: the hooks on macOS bash 3.2 and BSD tools (they avoid GNU-only features, but have run only on Linux), the sandbox itself, and the GitHub ruleset.

## Changing the guardrails

Edit this repository, open a pull request, let `self-test` pass, then rerun `sudo ./install/install.sh system` and `./install/install.sh user`. To allow another network host for sandboxed commands, add it to `sandbox.network.allowedDomains` in `global/managed-settings.json`.
