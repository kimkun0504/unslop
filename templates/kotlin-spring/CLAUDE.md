# Project

Kotlin 2.4 and Spring Boot 4 on Java 21, built with Gradle 9. Each direct subpackage of `com.example.app` is a Spring Modulith module; `ModularityTest` fails if a module reaches into another module's internals or creates a cycle.

- `scripts/setup` checks the pinned toolchain and resolves dependencies.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, ktlint, detekt with every rule, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% line and branch coverage and the build.
- `scripts/mutation` runs PIT and must report a 100% mutation score.

Parse input into value types whose constructors cannot produce invalid values, as `Money.parse` does. Errors reach HTTP clients as RFC 9457 problem details. Compiler warnings are errors.

You cannot edit Gradle files, the version catalog or `config/`. If you need a dependency, say which one and why in your final message.
