# Project

Go with the standard layout: `cmd/app` wires things together, `internal/cli` is the adapter, `internal/domain` is pure logic with no I/O. depguard enforces the direction.

- `scripts/setup` checks the toolchain and downloads modules.
- `scripts/fast-check` must pass before you stop: tidy, format, every golangci-lint linter, no comments, suppressions, tests.
- `scripts/verify` is what CI runs: fast-check plus the race detector, 100% coverage, fuzzing and a build.

Parse raw input into domain types at the boundary, as `ParseMoney` does. Wrap errors with `%w` and test them with `errors.Is`. Write output to an injected `io.Writer`, never `fmt.Print`. Tests live in `_test` packages and call `t.Parallel()`.

You cannot edit `go.mod`, `go.sum` or `.golangci.yml`. If you need a dependency, say which one and why in your final message.
