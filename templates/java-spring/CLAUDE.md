# Project

Java 25 and Spring Boot 4, built with Gradle 9. Each direct subpackage of `com.example.app` is a Spring Modulith module; `ModularityTest` fails if a module reaches into another module's internals or creates a cycle. Every package is `@NullMarked`, so NullAway rejects any unchecked null.

- `scripts/setup` checks the pinned toolchain and resolves dependencies.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, google-java-format, Error Prone with NullAway, `-Xlint:all -Werror`, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% line and branch coverage and the build.
- `scripts/mutation` runs PIT and must report a 100% mutation score.

Parse input into final classes whose private constructors cannot produce invalid values, as `Money.parse` does. Use records for data, `@Nullable` only where absence is real. Errors reach HTTP clients as RFC 9457 problem details. Never use `System.out`.

You cannot edit Gradle files or the version catalog. If you need a dependency, say which one and why in your final message.
