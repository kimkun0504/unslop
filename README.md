# unslop

**Make AI slop fail the build. Any stack.**

[![self-test](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml/badge.svg)](https://github.com/kimkun0504/unslop/actions/workflows/self-test.yml)

AI coding agents copy what they see and stop when they think they are done. Instructions in a `CLAUDE.md` are followed most of the time; checks that fail the build are followed every time. unslop turns engineering standards into those checks, for Claude Code and for every pull request.

## Add it to a repository

Requirements: `git`, `jq` (included in macOS 15 and later) and [`uv`](https://docs.astral.sh/uv/).

```bash
cd ~/code/my-service
uvx --from git+https://github.com/kimkun0504/unslop@v0.3.1 unslop init
```

`unslop init` detects the stacks, including a front end in a subfolder beside a back end, records today's lint and type findings as a baseline so only new code has to meet the bar, checks that the gate passes, and adds four files:

| File | What it is |
|---|---|
| `unslop.toml` | The stacks and their folders, the pinned unslop version and the time budget for the end-of-turn check |
| `.unslop/baseline.json` | Findings that existed on day one, counted per file and rule |
| `.claude/settings.json` | Turns on the unslop Claude Code plugin for this repository and makes build files, lockfiles, CI and the unslop files read-only for Claude |
| `.github/workflows/unslop.yml` | Runs the same check on every pull request |

If something is off, `unslop doctor` says what and how to fix it. Commit them on a branch and open a pull request. The next time you open Claude Code in the repository and trust the folder, the plugin installs itself. You can also install the plugin for yourself with `/plugin install unslop --marketplace kimkun0504/unslop`. Installed that way it runs in every repository you open: it blocks force pushes, hook bypasses and edits to Claude's own settings everywhere, and switches the rest on only where `unslop.toml` or a template's `.claude/unslop.json` exists. Once the repository is on GitHub, `unslop ruleset --apply` blocks merging until the check passes.

`unslop check` runs everything: no comments on added lines, no new suppressions or skipped tests, existing tests left alone, no lint or type finding beyond the baseline, formatted files stay formatted, tests pass, and every changed line is covered. Claude cannot end a turn while it fails. See [Adopting an existing repository](docs/adopting.md).

## Start a new project

```bash
uvx --from git+https://github.com/kimkun0504/unslop@v0.3.1 unslop new python ~/code/my-app
cd ~/code/my-app
scripts/setup
scripts/verify
```

A template is a small working app in the house style with the strictest gates for its stack and the plugin already turned on. `unslop list` shows every template and its gates.

## Turn it off

| To stop | Do this |
|---|---|
| unslop in one repository | Delete `unslop.toml`; the hooks go quiet there. Remove the other three files to clean up |
| The plugin for yourself | `/plugin disable unslop@unslop` in Claude Code |
| The optional machine layer | `sudo ./install/install.sh uninstall-system` from a clone of this repository |

## What you get

| Layer | Applies to | What it does | Details |
|---|---|---|---|
| **Plugin** | Repositories with `unslop.toml` or a template | Makes build and lint configs read-only for the agent, blocks history rewrites and hook bypasses, and refuses to let the agent stop while the check fails. Adds a reviewer agent and the `/unslop:spec`, `/unslop:long-run` and `/unslop:migration` skills | [Guardrails §2](docs/guardrails.md#2-project-layer) |
| **CI and GitHub** | Every pull request | Runs the same check; the ruleset blocks merging until it passes | [Guardrails §3](docs/guardrails.md#3-ci-and-github-layer) |
| **Machine**, optional | Every repository on your computer | Hides secrets and credentials, sandboxes shell commands behind a network allowlist, and makes the plugin's hooks impossible to switch off | [Guardrails §1](docs/guardrails.md#1-machine-layer) |
| **Claude profile**, optional | Your Claude Code sessions | A ten-line `CLAUDE.md` with working rules | [Guardrails §4](docs/guardrails.md#4-claude-profile-layer) |

The machine and profile layers need a clone of this repository:

```bash
git clone https://github.com/kimkun0504/unslop ~/Desktop/unslop
cd ~/Desktop/unslop
bash tests/hooks/run.sh
bash tests/install/run.sh
./install/install.sh user
sudo ./install/install.sh system
```

`sudo ./install/install.sh system` applies to every Claude Code session on the computer, so add it once you have tried unslop in a repository. `./install/install.sh check` shows what is installed, and `uninstall-system` and `uninstall-user` restore the files they replaced.

## Stacks

Every template ships a small working feature in the house style and passes the same contract: strict formatting, linting and types, enforced architecture boundaries, no comments, 100% coverage and, where a maintained tool exists, every mutant killed. Each is proven in CI by scaffolding a fresh project and planting violations that must be caught. Every profile for existing repositories is proven the same way against a sample legacy repository.

<!-- stacks:start -->
| Template | Format | Lint and types | Architecture | Tests | Mutation | Adopt profile |
|---|---|---|---|---|---|---|
| `python` | ruff format | ruff (all rules), basedpyright (all) | import-linter | pytest, hypothesis | mutmut | `python` |
| `ts-react` | prettier | typescript-eslint strict, tsc strictest, jsx-a11y | eslint-plugin-boundaries | vitest, testing-library, fast-check | Stryker | `typescript` |
| `go` | gofumpt | golangci-lint (all linters) | depguard | race detector, native fuzzing | none maintained | `go` |
| `kotlin-spring` | ktlint | detekt (all rules), warnings as errors | Spring Modulith | JUnit 5, Spring Boot | PIT | `jvm` |
| `java-spring` | google-java-format | Error Prone, NullAway (JSpecify), `-Xlint:all -Werror` | Spring Modulith | JUnit 5, AssertJ, Spring Boot | PIT | `jvm` |
| `terraform` | terraform fmt | tflint (all rules, AWS), validate, checkov | single-purpose modules | `terraform test` with mocked providers | none available | `terraform` |
| `rust` | rustfmt | clippy (all, pedantic, nursery, restriction), `#[allow]` denied | workspace crates, I/O banned in domain | cargo test, proptest | cargo-mutants | `rust` |
| `dotnet` | dotnet format | all analyzers as errors, nullable reference types | domain references only core framework | xUnit v3, WebApplicationFactory | Stryker.NET | `dotnet` |
| `php` | PHP-CS-Fixer | PHPStan max + strict rules, native types only | deptrac, I/O banned in domain | PHPUnit 13 | Infection | `php` |
| `ruby` | RuboCop | RuboCop with every cop, Steep strict on RBS | RuboCop guards: pure domain, output through ports | RSpec | mutant | `ruby` |
| `elixir` | mix format | Credo strict, compiler types, Dialyzer | Boundary, I/O banned in domain | ExUnit + StreamData | none yet | `elixir` |
| `swift` | swift-format | SwiftLint (all opt-in), Swift 6 strict concurrency | SwiftPM targets, I/O banned in domain | Swift Testing | none yet | `swift` |

| Adopt profile | For | Format, on changed files | Lint and types, ratcheted | Tests and changed-line coverage |
|---|---|---|---|---|
| `python` | Python: uv, Poetry or pip projects | ruff format | ruff (all rules), basedpyright strict | pytest with branch coverage |
| `typescript` | TypeScript and JavaScript: npm, pnpm or Yarn projects | prettier, when the project uses it | tsc with strictest flags, the project's ESLint config | vitest or jest with coverage |
| `go` | Go: a go.mod at the root | gofmt | golangci-lint (all linters) | go test -race with coverage |
| `jvm` | Java and Kotlin: Gradle or Maven builds | none; the project's own formatter | PMD for Java, detekt (all rules) for Kotlin | JaCoCo added without editing the build |
| `terraform` | Terraform: .tf files | terraform fmt | tflint (all rules, AWS), checkov | terraform test, when the repository has tests |
| `rust` | Rust: a Cargo.toml at the root | rustfmt | clippy pedantic and nursery, no unwrap, expect, panic or print outside tests | cargo llvm-cov |
| `dotnet` | C# and .NET: a solution or project file at the root | none; the project's own formatter | all .NET analyzers, code style and nullable warnings from the build | dotnet test with Coverlet |
| `php` | PHP: composer.json | none; the project's own formatter | PHPStan at max level | PHPUnit with clover coverage of src, app and lib |
| `ruby` | Ruby: a Gemfile | RuboCop layout cops, in the project's style | RuboCop with the project's config plus new cops and the performance and RSpec plugins | RSpec or rake test, with coverage through Ruby's Coverage module |
| `elixir` | Elixir: mix.exs | mix format | compiler warnings, Credo strict when the project uses Credo | mix test with cover, converted for diff coverage |
| `swift` | Swift: Package.swift | swift format, when the project has a .swift-format | SwiftLint defect rules on top of the project's config, compiler warnings with complete strict concurrency | swift test with llvm-cov |
<!-- stacks:end -->

The tables are generated from [`templates/catalog.json`](templates/catalog.json); `unslop list` shows the same in the terminal. To add a stack, follow [Adding a stack](docs/adding-a-stack.md).

Every template has the same commands:

| Command | Runs | Used by |
|---|---|---|
| `scripts/setup` | Installs locked dependencies, checks the pinned toolchain | You, CI |
| `scripts/fast-check` | Format, lint, types, comments, architecture, suppressions, tests | The end-of-turn check |
| `scripts/verify` | `fast-check` plus coverage and the build | CI |
| `scripts/mutation` | Mutation testing; every mutant must be killed | CI |

## Commands

| Command | What it does |
|---|---|
| `unslop init [--stack PROFILE[:FOLDER]]…` | Add unslop to the current repository and record the baseline; stacks are detected when left out |
| `unslop check [--base REF]` | Run every gate against the changes since the base branch |
| `unslop setup` | Install the repository's dependencies the way the profile expects |
| `unslop baseline` | Record the current findings as the baseline. For humans, after fixing old findings; Claude is blocked from running it |
| `unslop plan` | Print the exact commands each gate runs |
| `unslop doctor` | Explain what is missing for unslop to work here: tools, pins, the plugin, the ruleset |
| `unslop upgrade` | Move `unslop.toml`, the plugin pin and the CI action to the version you run it with |
| `unslop ruleset [--apply]` | Print or apply the GitHub branch ruleset |
| `unslop new TEMPLATE DIR` | Start a new project from a template |
| `unslop list` | Show templates, their gates and the profiles for existing repositories |

## Documentation

| Read | To learn |
|---|---|
| [Adopting an existing repository](docs/adopting.md) | Baselines, ratchets, changed-line coverage, and how to tune the commands |
| [Guardrail catalog](docs/guardrails.md) | Every guardrail, its mechanism, and how hard it is to get around |
| [Engineering standards](docs/standards.md) | The architecture, domain, API, data, testing, security and delivery standards, and which ones a tool enforces today |
| [Workflow](docs/workflow.md) | Spec first, test first, long unattended runs, what to do when a guardrail blocks Claude |
| [Adding a stack](docs/adding-a-stack.md) | The template contract and how a new stack is proven |
| [Releasing](docs/releasing.md) | Tagging a version, and publishing to PyPI |
| [Known limits](docs/limits.md) | What is not yet guaranteed |

## Repository layout

```text
src/unslop/        the unslop command: init, check, baseline, new and the per-stack profiles
plugin/            the Claude Code plugin: hooks, reviewer agent, skills
action.yml         the GitHub Action the generated workflow uses
templates/         one folder per stack, plus catalog.json
common/            files every new project gets: decision records, check scripts, comment checker, settings
global/            the optional machine layer and Claude profile
install/           installer for the machine and profile layers
tests/             package tests, hook tests, the stack contract check, adoption fixtures
docs/              the documentation above
```

## Changing the guardrails

Edit this repository in a pull request and let `self-test` pass, then release a new version (see [Releasing](docs/releasing.md)). Repositories move to it with `unslop upgrade` run from the new version, which updates `unslop.toml`, `.claude/settings.json` and `.github/workflows/unslop.yml` together; `unslop check` refuses to run when they disagree. To allow another network host for sandboxed commands, add it to `sandbox.network.allowedDomains` in `global/managed-settings.json`.
