# Engineering standards

The standards every unslop project follows, and how each one is held in place. The status column is honest about which ones a machine checks today.

| Status | Meaning |
|---|---|
| **Enforced** | A tool fails the build. The cell names the tool and which templates use it. |
| **Shown** | The template's example code demonstrates it, so agents copy it. |
| **Reviewed** | The `reviewer` agent checks it against decision record 0003. |
| **Planned** | The right standard, not yet automated in the templates. |

## 1. Architecture

| Standard | Why | Status |
|---|---|---|
| Start as a modular monolith; split into services only for a proven scaling or ownership need | One deployable is far cheaper to change, test and run | Shown in every template |
| Dependencies point inward: adapters (HTTP, CLI, database) depend on the domain, never the reverse | Business rules stay testable without I/O | Enforced: import-linter (Python), eslint-plugin-boundaries (TS), depguard (Go), Spring Modulith (Kotlin) |
| The domain does no I/O ("functional core, imperative shell") | Pure logic is easy to test and mutate | Enforced for Python and Go domain packages; Reviewed elsewhere |
| No grab-bag modules: `utils`, `helpers`, `common`, `shared` | They collect unrelated code and blur boundaries | Enforced in TS (`no-restricted-imports`); Reviewed elsewhere |
| Deep modules: a small interface over substantial behaviour; no pass-through layers | Shallow layers add cost without hiding anything | Reviewed |
| Build only what a current requirement needs (YAGNI) | Speculative abstractions are the most common agent slop | Reviewed |
| Significant decisions are recorded as MADR decision records with a Confirmation line naming the check that enforces them | Decisions become inputs agents can read, and each has a test | Shown in `docs/decisions/` |
| Complexity limits: function length, cyclomatic and cognitive complexity, nesting, parameter count | Keeps every unit reviewable | Enforced: ruff PLR and C90, ESLint, golangci-lint cyclop, gocognit and funlen, detekt |

## 2. Domain modelling

| Standard | Why | Status |
|---|---|---|
| Parse, don't validate: turn raw input into a domain type once, at the boundary | Invalid data cannot travel inward | Shown: `Money.parse` in every template |
| Make illegal states unrepresentable: private constructors, sealed types, enums instead of flags | The compiler rejects whole classes of bugs | Shown; Reviewed |
| No primitive obsession for money, identifiers or units | `int cents` and `String id` mix silently | Shown |
| Errors are typed: result types or dedicated exception classes that build their own message | Callers can handle them precisely | Shown; Enforced in Python (ruff EM, TRY) and Go (errorlint, err113, wrapcheck) |
| Exhaustive handling of enums and unions | Adding a case cannot silently fall through | Enforced: `switch-exhaustiveness-check` (TS), `exhaustive` (Go), Kotlin `when` |
| No type escapes: no `any`, type assertions, non-null assertions or `!!` | They switch the type checker off | Enforced: typescript-eslint, basedpyright `all`, Kotlin guard |

## 3. APIs and contracts

| Standard | Why | Status |
|---|---|---|
| Contract first: OpenAPI for HTTP, AsyncAPI for events, protobuf for RPC; clients are generated | Removes ambiguity for both sides and for agents | Planned |
| Lint the contract: Spectral with the OWASP API Security ruleset | Catches insecure and inconsistent APIs before code | Planned |
| Fail CI on breaking changes: `oasdiff breaking --fail-on ERR`, `buf breaking` | Consumers never break by accident | Planned |
| Errors use RFC 9457 problem details (`application/problem+json`) | One machine-readable error shape | Shown and tested in Kotlin; Reviewed elsewhere |
| Retries are safe: idempotency keys on unsafe methods (IETF draft) | Duplicate requests do not duplicate effects | Reviewed |
| Event schemas evolve compatibly: registry compatibility BACKWARD or stricter, transactional outbox for publishing | Consumers keep working across deploys | Planned |

## 4. Data and migrations

| Standard | Why | Status |
|---|---|---|
| Versioned migrations, immutable once applied | History is reproducible | Enforced: `protect-paths.sh` blocks edits to existing migrations |
| Migrations are linted: Squawk for Postgres, Atlas analyzers for destructive and incompatible changes | Locks and rewrites are caught before production | Planned for a database template; procedure in `/unslop-migration` |
| Expand, migrate, contract: add, backfill in batches, switch code, drop later | Zero-downtime deploys | Procedure in `/unslop-migration` |
| Every migration sets `lock_timeout` and `statement_timeout`; indexes use `CONCURRENTLY`; constraints are added `NOT VALID` and validated later | Avoids table-wide locks | Procedure; enforced by Squawk when added |
| Keys are `bigint GENERATED ALWAYS AS IDENTITY` or `uuidv7()`; times are `timestamptz`; integrity lives in database constraints | The database guards its own invariants | Procedure |
| Tests run against real Postgres (Testcontainers), not mocks or SQLite | Behaviour matches production | Planned |
| Agents never hold production credentials; any agent database access uses a read-only role; backups sit outside the agent's reach | Agent-caused database deletions in 2025 and 2026 all shared these three failures | Enforced locally by M2 and M12; the rest is environment setup |

## 5. Testing

| Standard | Why | Status |
|---|---|---|
| Write the failing test first, then the code | Proves the test can fail | Reviewed; tests lockable with `.claude/tests.locked` |
| Existing tests are never weakened, skipped or deleted to get green | The most common way agents fake success | Enforced: `check-diff` (P8, P9) |
| 100% line and branch coverage of application code | A floor: untested code is unreviewed code | Enforced in all four templates |
| Every mutant killed | Coverage shows code ran; mutation shows tests would notice a change | Enforced: mutmut, Stryker, PIT, cargo-mutants, Stryker.NET, Infection, mutant; Go relies on fuzzing |
| Property-based or fuzz tests for parsers and arithmetic | Finds the inputs nobody thought of | Shown: hypothesis, fast-check, Go native fuzzing |
| Test through public behaviour: roles and labels in UIs, HTTP in services | Tests survive refactoring | Shown |

## 6. Errors, logging and observability

| Standard | Why | Status |
|---|---|---|
| No swallowed errors and no ignored results | Silent failures are the hardest bugs | Enforced: ruff BLE, SIM105, typescript-eslint `no-floating-promises`, errcheck, basedpyright `reportUnusedCallResult` |
| No `print`, `console.log`, `fmt.Println` or `println`; output goes through an injected writer or a structured logger | Logs stay structured and testable | Enforced: ruff T20, ESLint `no-console`, forbidigo, Kotlin guard |
| OpenTelemetry for traces, metrics and logs, with correlation IDs | One vendor-neutral signal pipeline | Planned |
| Health and readiness endpoints, and SLOs for user-facing paths | Operations need a definition of healthy | Planned |

## 7. Security

| Standard | Why | Status |
|---|---|---|
| Follow OWASP Top 10:2025 and ASVS for web applications | The shared baseline for application risk | Reviewed |
| Validate at the boundary, parameterise every query, deny by default in authorisation | Covers the most exploited classes | Shown (boundary parsing); Reviewed |
| Secrets live in a secret manager, never in the repository or the agent's environment | Agents and logs leak what they can see | Enforced locally by M1 and M2 |
| Dependencies: lockfiles enforced, release-age delay, vulnerability audit in CI | Supply-chain attacks target fresh releases | Enforced: uv `exclude-newer` 7 days, pnpm `minimumReleaseAge` 1 day, pip-audit, pnpm audit, govulncheck |
| Actions pinned to commit SHAs with read-only tokens | Tag hijacks (such as the March 2026 Trivy compromise) cannot reach CI | Enforced by the contract check |
| Build provenance: SBOMs and SLSA v1.2 attestations for released artifacts | Consumers can verify what they run | Planned |
| Containers: minimal or distroless base, non-root, pinned digests, linted with hadolint | Smaller attack surface, reproducible builds | Planned |

## 8. Front end

| Standard | Why | Status |
|---|---|---|
| Style only with design tokens: no arbitrary Tailwind values, no inline styles, no unknown classes | Prevents generic, inconsistent UI | Enforced: eslint-plugin-better-tailwindcss and `no-restricted-syntax` |
| Accessibility: jsx-a11y strict, and tests that query by role and label | Accessible UIs are also testable UIs | Enforced and Shown |
| Core Web Vitals budgets at the 75th percentile: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1, checked with Lighthouse CI | Performance regressions fail like bugs | Planned |
| Named exports only; no unused exports or files | Searchable code, no dead code | Enforced: `no-restricted-syntax`, knip |

## 9. Delivery and infrastructure

| Standard | Why | Status |
|---|---|---|
| Trunk-based: short-lived branches, pull requests, required checks, linear history | Small reviewable changes | Enforced by the ruleset (G1 to G3) |
| Agents plan; humans or CI apply. No agent `terraform apply`, `kubectl apply` or `helm upgrade` | An agent deleted a production database and its snapshots with `terraform destroy` in February 2026 | Enforced locally by M11 |
| GitOps: Argo CD deploys from Git, with sync windows and manual sync for production | Every change is reviewed and reversible | Planned |
| Toolchains pinned per project (mise) and in CI | The same versions everywhere | Enforced in Go and Kotlin; pinned in CI for all |
| Dependency updates through Renovate with release-age delay and digest pinning | Fresh but not reckless | Planned |

## 10. Review rubric

The `reviewer` agent blocks a change only for a concrete failing scenario in one of these areas, following Google's code review guide. It skips style, which tools already enforce.

1. An acceptance criterion in `SPEC.md` is not met, or has no test that proves it.
2. Correctness or security fails for a specific input.
3. A speculative abstraction, option or extension point has no current caller.
4. Untyped input is checked deep inside instead of parsed once at the boundary.
5. A combination of booleans or nullable fields allows a state that should be impossible.
6. A layer only passes calls through, or an interface is as large as its implementation.
7. Business logic performs I/O.
8. A test would still pass with the behaviour deleted.
9. The change contradicts an accepted decision record.
10. An error is not a problem detail, an API change breaks consumers, or a new event field is required.

## Sources

- Google, [What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Alexis King, [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/); Yaron Minsky, [Effective ML revisited](https://blog.janestreet.com/effective-ml-revisited/)
- [MADR decision records](https://adr.github.io/madr/)
- [RFC 9457 problem details](https://www.rfc-editor.org/rfc/rfc9457.html); [Idempotency-Key header draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)
- [Spectral OWASP ruleset](https://github.com/stoplightio/spectral-owasp-ruleset); [oasdiff breaking changes](https://github.com/oasdiff/oasdiff/blob/main/docs/BREAKING-CHANGES.md); [buf breaking](https://buf.build/docs/breaking/)
- [Confluent schema evolution](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Squawk rules](https://squawkhq.com/docs/rules); [Atlas lint analyzers](https://atlasgo.io/lint/analyzers); [GitLab migration style guide](https://docs.gitlab.com/development/migration_style_guide/); [strong_migrations](https://github.com/ankane/strong_migrations); [pgroll](https://github.com/xataio/pgroll)
- [OpenTelemetry language status](https://opentelemetry.io/docs/languages/)
- [SLSA v1.2](https://slsa.dev/spec/v1.2/build-requirements); [hadolint](https://github.com/hadolint/hadolint)
- [Core Web Vitals](https://web.dev/articles/vitals)
- [Argo CD sync windows](https://argo-cd.readthedocs.io/en/stable/user-guide/sync_windows/)
- Alexey Grigorev, [How I dropped our production database](https://aishippingblog.com/p/how-i-dropped-our-production-database); Datadog, [SQL injection in the PostgreSQL MCP server](https://securitylabs.datadoghq.com/articles/mcp-vulnerability-case-study-SQL-injection-in-the-postgresql-mcp-server/)
