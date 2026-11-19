# Project

C# on .NET 10 LTS. `src/App.Domain` holds pure logic and may reference only core framework assemblies (`ArchitectureTests` enforces this); `src/App.Api` is a minimal API that maps domain errors to RFC 9457 problem details. Packages are versioned centrally in `Directory.Packages.props` with lockfiles.

- `scripts/setup` checks the SDK pinned in `global.json`, restores tools and locked packages.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, `dotnet format`, a build with every analyzer as an error, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% line and branch coverage and a release build.
- `scripts/mutation` runs Stryker.NET and must report a 100% score.

Parse input into sealed classes with private constructors, as `Money.Parse` does. Nullable reference types are on; never use `!` outside tests. Pass `CultureInfo.InvariantCulture` and `StringComparison.Ordinal` explicitly. `#pragma warning disable` and `[SuppressMessage]` are rejected.

You cannot edit project files, `Directory.*.props`, `global.json`, `.editorconfig`, lockfiles or tool manifests. If you need a package, say which one and why in your final message.
