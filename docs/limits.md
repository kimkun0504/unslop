# Known limits

What unslop does not yet guarantee, so nothing here is mistaken for a promise.

| Area | Limit | Mitigation |
|---|---|---|
| macOS | The hooks have run only on Linux. They avoid GNU-only features, but macOS bash 3.2 and BSD tools are untested. | Run `bash tests/hooks/run.sh` on your Mac after cloning; it should report 112 passed. |
| Sandbox and ruleset | Configuration rather than code, so nothing here tests them. | Run `/sandbox` in Claude Code, and try a direct push to `main` once the ruleset is applied. |
| Shell command guard | Matches text. A command hidden in a variable (`G=git; $G push --force`) gets past it. | The sandbox, the missing credentials and the ruleset are the real boundary; the guard catches ordinary mistakes. |
| Read tool | Deny rules on the Read tool match paths, not file contents opened by scripts. | Shell scripts run sandboxed with `denyRead` on credential folders. |
| Kotlin | detekt 1.23 bundles an older Kotlin compiler, so its type-aware rules do nothing on Kotlin 2.4. | The Kotlin guard bans `println`, `print`, `TODO` and `!!` by parsing. Move to detekt 2 when it is stable. |
| Kotlin mutation | PIT skips calls into `kotlin.jvm.internal`, the null checks the compiler inserts, which no test can observe. | None needed; the remaining mutants are all killed. |
| Go mutation | The Go mutation tools are unmaintained, so the Go template has no mutation gate. | Native fuzzing, the race detector and 100% coverage. |
| Cloud sessions | Claude Code on the web does not load repository hooks or permission rules. | CI and the ruleset still apply to every pull request. |
| `allowManagedHooksOnly` | Left off, because turning it on disables `/goal`. A project could add its own hooks. | Project hooks cannot remove the managed hooks, which always run. |
| Planned standards | Several standards in [standards.md](standards.md) are marked Planned: API contract linting, migration linting in a database template, OpenTelemetry, container and IaC templates, Web Vitals budgets. | Each will land as a template or gate with its own CI proof. |
