# Project

Swift 6.4 with SwiftPM, Swift 6 language mode and strict concurrency. Targets enforce the layers at compile time: `Domain` depends on nothing, `CLI` on `Domain`, and the `app` executable only wires the process streams.

- `scripts/setup` checks Swift, installs a checksum-verified SwiftLint into `.tools/` and builds.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, `swift format lint --strict`, SwiftLint with every opt-in rule that does not fight the formatter, a build with all warnings as errors, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% line, region and function coverage of `Domain` and `CLI`.

`Domain` imports nothing but the standard library: no Foundation, files, clock or randomness. Output goes through the `Output` protocol, never `print`. Value types validate their input and use typed throws, as `Money.parse` does. Tests use Swift Testing with parameterized `@Test(arguments:)`.

You cannot edit `Package.swift`, `Package.resolved`, `.swift-version`, `.swiftlint.yml`, `.swift-format` or anything in `tools/guard`. If you need a package, say which one and why in your final message.
