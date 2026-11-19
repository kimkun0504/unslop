# unslop

**Make AI slop fail the build. Any stack.**

[![self-test](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml/badge.svg)](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml)

AI coding agents copy what they see and stop when they think they are done. Instructions in a `CLAUDE.md` are followed most of the time; checks that fail the build are followed every time. unslop turns engineering standards into those checks, for Claude Code and for every pull request.

## What you get

| Layer | Applies to | What it does | Details |
|---|---|---|---|
| **Machine** | Every repository on your computer | Hides secrets and credentials, sandboxes shell commands behind a network allowlist, blocks history rewrites, hook bypasses and infrastructure or database mutations | [Guardrails §1](docs/guardrails.md#1-machine-layer) |
| **Project** | Projects created from a template | Makes build and lint configs read-only for the agent, bans comments and suppressions, protects existing tests, and refuses to let the agent stop while checks fail | [Guardrails §2](docs/guardrails.md#2-project-layer) |
| **CI and GitHub** | Every pull request | Runs the same checks plus mutation testing and audits; the ruleset blocks merging until they pass | [Guardrails §3](docs/guardrails.md#3-ci-and-github-layer) |
| **Claude profile** | Your Claude Code sessions | A ten-line `CLAUDE.md`, a read-only reviewer agent, and skills for specs, migrations and long runs | [Guardrails §4](docs/guardrails.md#4-claude-profile-layer) |

## Quick start

Requirements: `git`, `jq` (included in macOS 15 and later), `perl` and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kimkun0504/unslop ~/Desktop/unslop
cd ~/Desktop/unslop
bash tests/hooks/run.sh
sudo ./install/install.sh system
./install/install.sh user
```

Then start a project:

```bash
~/Desktop/unslop/bin/unslop new python ~/code/my-app
cd ~/code/my-app
scripts/setup
scripts/verify
gh api -X POST repos/OWNER/REPO/rulesets --input .github/rulesets/main.json
```

In Claude Code, run `/unslop-spec` to write the spec, then `/unslop-long-run` for an unattended build. See [the workflow guide](docs/workflow.md).

## Stacks

Every template ships a small working feature in the house style and passes the same contract: strict formatting, linting and types, enforced architecture boundaries, no comments, 100% coverage and, where a maintained tool exists, every mutant killed. Each is proven in CI by scaffolding a fresh project and planting violations that must be caught.

| Template | Format | Lint and types | Architecture | Tests | Mutation |
|---|---|---|---|---|---|
| `python` | ruff format | ruff (all rules), basedpyright (all) | import-linter | pytest, hypothesis | mutmut |
| `ts-react` | prettier | typescript-eslint strict, tsc strictest, jsx-a11y | eslint-plugin-boundaries | vitest, testing-library, fast-check | Stryker |
| `go` | gofumpt | golangci-lint (all linters) | depguard | race detector, native fuzzing | none maintained |
| `kotlin-spring` | ktlint | detekt (all rules), warnings as errors | Spring Modulith | JUnit 5, Spring Boot | PIT |
| `java-spring` | google-java-format | Error Prone, NullAway (JSpecify), `-Xlint:all -Werror` | Spring Modulith | JUnit 5, AssertJ, Spring Boot | PIT |
| `rust` | rustfmt | clippy (all, pedantic, nursery, restriction), `#[allow]` denied | workspace crates, I/O banned in domain | cargo test, proptest | cargo-mutants |
| `dotnet` | dotnet format | all analyzers as errors, nullable reference types | domain references only core framework | xUnit v3, WebApplicationFactory | Stryker.NET |
| `php` | PHP-CS-Fixer | PHPStan max + strict rules, native types only | deptrac, I/O banned in domain | PHPUnit 13 | Infection |
| `ruby` | RuboCop | RuboCop with every cop, Steep strict on RBS | RuboCop guards: pure domain, output through ports | RSpec | mutant |
| `terraform` | terraform fmt | tflint (all rules, AWS), validate, checkov | single-purpose modules | `terraform test` with mocked providers | none available |

The full gate list per template is in [`templates/catalog.json`](templates/catalog.json). Next stacks: Elixir and Swift. To add one, follow [Adding a stack](docs/adding-a-stack.md).

Every template has the same commands:

| Command | Runs | Used by |
|---|---|---|
| `scripts/setup` | Installs locked dependencies, checks the pinned toolchain | You, CI |
| `scripts/fast-check` | Format, lint, types, comments, architecture, suppressions, tests | The end-of-session check |
| `scripts/verify` | `fast-check` plus coverage and the build | CI |
| `scripts/mutation` | Mutation testing; every mutant must be killed | CI |

## Documentation

| Read | To learn |
|---|---|
| [Guardrail catalog](docs/guardrails.md) | Every guardrail, its mechanism, and how hard it is to get around |
| [Engineering standards](docs/standards.md) | The architecture, domain, API, data, testing, security and delivery standards, and which ones a tool enforces today |
| [Workflow](docs/workflow.md) | Spec first, test first, long unattended runs, what to do when a guardrail blocks Claude |
| [Adding a stack](docs/adding-a-stack.md) | The template contract and how a new stack is proven |
| [Known limits](docs/limits.md) | What is not yet guaranteed |

## Repository layout

```text
global/            machine and profile layer: managed settings, hooks, CLAUDE.md, reviewer agent, skills
install/           installer for the machine and profile layers
common/            files every project gets: decision records, check scripts, comment checker, settings
templates/         one folder per stack, plus catalog.json
bin/unslop         scaffolds a project from a template
tests/             hook tests, comment checker tests, the stack contract check
docs/              the documentation above
```

## Changing the guardrails

Edit this repository in a pull request and let `self-test` pass. Then rerun `sudo ./install/install.sh system` and `./install/install.sh user`. To allow another network host for sandboxed commands, add it to `sandbox.network.allowedDomains` in `global/managed-settings.json`.
