# unslop

**Make AI slop fail the build. Any stack.**

[![self-test](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml/badge.svg)](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml)

AI coding agents copy what they see and stop when they think they are done. Instructions in a `CLAUDE.md` are followed most of the time; checks that fail the build are followed every time. unslop turns engineering standards into those checks, for Claude Code and for every pull request.

## What you get

| Layer | Applies to | What it does | Details |
|---|---|---|---|
| **Machine** | Every repository on your computer | Hides secrets and credentials, sandboxes shell commands behind a network allowlist, blocks history rewrites, hook bypasses and infrastructure or database mutations | [Guardrails §1](docs/guardrails.md#1-machine-layer) |
| **Project** | Projects created from a template or adopted with `unslop adopt` | Makes build and lint configs read-only for the agent, bans comments and suppressions, protects existing tests, and refuses to let the agent stop while checks fail | [Guardrails §2](docs/guardrails.md#2-project-layer) |
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

`unslop new` and `unslop adopt` put your GitHub handle in `CODEOWNERS` and your name in the decision records. They read `UNSLOP_OWNER` and `UNSLOP_OWNER_NAME`, falling back to `gh` and your git config.

Or bring an existing repository under the same guardrails, with its current findings recorded as a baseline so only new code has to meet the bar:

```bash
~/Desktop/unslop/bin/unslop adopt python ~/code/my-service
```

See [Adopting an existing repository](docs/adopting.md).

In Claude Code, run `/unslop-spec` to write the spec, then `/unslop-long-run` for an unattended build. See [the workflow guide](docs/workflow.md).

## Stacks

Every template ships a small working feature in the house style and passes the same contract: strict formatting, linting and types, enforced architecture boundaries, no comments, 100% coverage and, where a maintained tool exists, every mutant killed. Each is proven in CI by scaffolding a fresh project and planting violations that must be caught.

<!-- stacks:start -->
| Template | Format | Lint and types | Architecture | Tests | Mutation | Adopt profile |
|---|---|---|---|---|---|---|
| `python` | ruff format | ruff (all rules), basedpyright (all) | import-linter | pytest, hypothesis | mutmut | `python` |
| `ts-react` | prettier | typescript-eslint strict, tsc strictest, jsx-a11y | eslint-plugin-boundaries | vitest, testing-library, fast-check | Stryker | `typescript` |
| `go` | gofumpt | golangci-lint (all linters) | depguard | race detector, native fuzzing | none maintained | `go` |
| `kotlin-spring` | ktlint | detekt (all rules), warnings as errors | Spring Modulith | JUnit 5, Spring Boot | PIT | `jvm` |
| `java-spring` | google-java-format | Error Prone, NullAway (JSpecify), `-Xlint:all -Werror` | Spring Modulith | JUnit 5, AssertJ, Spring Boot | PIT | `jvm` |
| `terraform` | terraform fmt | tflint (all rules, AWS), validate, checkov | single-purpose modules | `terraform test` with mocked providers | none available | `terraform` |
| `rust` | rustfmt | clippy (all, pedantic, nursery, restriction), `#[allow]` denied | workspace crates, I/O banned in domain | cargo test, proptest | cargo-mutants | not yet |
| `dotnet` | dotnet format | all analyzers as errors, nullable reference types | domain references only core framework | xUnit v3, WebApplicationFactory | Stryker.NET | not yet |
| `php` | PHP-CS-Fixer | PHPStan max + strict rules, native types only | deptrac, I/O banned in domain | PHPUnit 13 | Infection | not yet |
| `ruby` | RuboCop | RuboCop with every cop, Steep strict on RBS | RuboCop guards: pure domain, output through ports | RSpec | mutant | not yet |
| `elixir` | mix format | Credo strict, compiler types, Dialyzer | Boundary, I/O banned in domain | ExUnit + StreamData | none yet | not yet |

| Adopt profile | For | Format, on changed files | Lint and types, ratcheted | Tests and changed-line coverage |
|---|---|---|---|---|
| `python` | Python: uv, Poetry or pip projects | ruff format | ruff (all rules), basedpyright (all) | pytest with branch coverage |
| `typescript` | TypeScript and JavaScript: npm, pnpm or Yarn projects | prettier, when the project uses it | tsc with strictest flags, the project's ESLint config | vitest or jest with coverage |
| `go` | Go: a go.mod at the root | gofmt | golangci-lint (all linters) | go test -race with coverage |
| `jvm` | Java and Kotlin: Gradle or Maven builds | none; the project's own formatter | PMD for Java, detekt (all rules) for Kotlin | JaCoCo added without editing the build |
| `terraform` | Terraform: .tf files | terraform fmt | tflint (all rules, AWS), checkov | terraform test, when the repository has tests |
<!-- stacks:end -->

The tables are generated from [`templates/catalog.json`](templates/catalog.json), which also lists every gate per template; run `bin/unslop list` to see it in the terminal. Adopt profiles bring the same checks to an existing repository; see [Adopting an existing repository](docs/adopting.md). Next stack: Swift. To add one, follow [Adding a stack](docs/adding-a-stack.md).

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
| [Adopting an existing repository](docs/adopting.md) | Baselines, ratchets and changed-line coverage for code that already exists |
| [Adding a stack](docs/adding-a-stack.md) | The template contract and how a new stack is proven |
| [Known limits](docs/limits.md) | What is not yet guaranteed |

## Repository layout

```text
global/            machine and profile layer: managed settings, hooks, CLAUDE.md, reviewer agent, skills
install/           installer for the machine and profile layers
common/            files every project gets: decision records, check scripts, comment checker, settings
templates/         one folder per stack, plus catalog.json
adopt/             files and per-stack profiles for adopting an existing repository
bin/unslop         new, adopt and list
tests/             hook tests, guard tests, the stack contract check, adoption fixtures
docs/              the documentation above
```

## Changing the guardrails

Edit this repository in a pull request and let `self-test` pass. Then rerun `sudo ./install/install.sh system` and `./install/install.sh user`. To allow another network host for sandboxed commands, add it to `sandbox.network.allowedDomains` in `global/managed-settings.json`.
