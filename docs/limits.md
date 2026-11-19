# Known limits

What unslop does not yet guarantee, so nothing here is mistaken for a promise.

| Area | Limit | Mitigation |
|---|---|---|
| macOS | The hooks have run only on Linux. They avoid GNU-only features, but macOS bash 3.2 and BSD tools are untested. | Run `bash tests/hooks/run.sh` on your Mac after cloning; it should end with `0 failed`. |
| Sandbox and ruleset | Configuration rather than code, so nothing here tests them. | Run `/sandbox` in Claude Code, and try a direct push to `main` once the ruleset is applied. |
| Shell command guard | Matches text. A command hidden in a variable (`G=git; $G push --force`) gets past it. | The sandbox, the missing credentials and the ruleset are the real boundary; the guard catches ordinary mistakes. |
| Read tool | Deny rules on the Read tool match paths, not file contents opened by scripts. | Shell scripts run sandboxed with `denyRead` on credential folders. |
| Kotlin | detekt 1.23 bundles an older Kotlin compiler, so its type-aware rules do nothing on Kotlin 2.4. | The Kotlin guard bans `println`, `print`, `TODO` and `!!` by parsing. Move to detekt 2 when it is stable. |
| Kotlin mutation | PIT skips calls into `kotlin.jvm.internal`, the null checks the compiler inserts, which no test can observe. | None needed; the remaining mutants are all killed. |
| Go mutation | The Go mutation tools are unmaintained, so the Go template has no mutation gate. | Native fuzzing, the race detector and 100% coverage. |
| .NET mutation | Stryker.NET's Microsoft Testing Platform runner is marked preview. Stryker 4 silently tested nothing under this platform and still exited 0. | `scripts/mutation` passes only when Stryker reports a final score of 100%, and lists every surviving mutant otherwise. |
| Ruby mutation | mutant is free only for open source. The template sets `usage: opensource` in `.mutant.yml`. | A commercial project buys a mutant licence and sets `usage: commercial`, or removes `scripts/mutation` and says so in its README. |
| Ruby supply chain | Bundler has no minimum release age, unlike the uv and pnpm templates. | The lockfile is installed in frozen mode and `bundle-audit` runs in CI; Renovate can add a release-age delay. |
| Terraform mutation | No maintained mutation tool exists for Terraform. | Every secure default and input validation is asserted in `terraform test`, and checkov scans the plan. |
| Where templates were built | Python, TypeScript, Go and Rust were built and tested locally and in CI. Kotlin, Java, Terraform, .NET, PHP and Ruby could only be built in CI, because their package registries are blocked in the build session. | Every template is proven the same way in CI: scaffold, verify, mutation and planted violations. |
| Cloud sessions | Claude Code on the web does not load repository hooks or permission rules. | CI and the ruleset still apply to every pull request. |
| `allowManagedHooksOnly` | Left off, because turning it on disables `/goal`. A project could add its own hooks. | Project hooks cannot remove the managed hooks, which always run. |
| Adopted repositories | Architecture rules, mutation testing and dead-code checks are not adopted, because they depend on a layout the repository may not have. detekt runs without type resolution, so its type-aware rules are inactive; the Kotlin guard covers `println`, `TODO` and `!!`. | Add architecture rules per repository once the layers exist, or move the code into a template project. |
| Adopted coverage | Changed lines in files the coverage tool does not measure, such as code outside the configured source folder, are not checked. | Keep new code inside the measured source folders, or widen the source in `.unslop/adopt.json`. |
| Adopted baselines | Counts are per file and rule, so renaming a file with findings makes them look new. A file that is deleted and recreated loses its allowance. | A human runs `scripts/rebaseline` in the pull request that renames the file. |
| Large repositories | `fast-check` in an adopted repository lints the whole repository and runs every test, which can exceed the end-of-session check's 240-second limit. | Narrow the test command in `.unslop/adopt.json` to a fast subset; CI still runs the full suite. |
| Planned standards | Several standards in [standards.md](standards.md) are marked Planned: API contract linting, migration linting in a database template, OpenTelemetry, container and IaC templates, Web Vitals budgets. | Each will land as a template or gate with its own CI proof. |
