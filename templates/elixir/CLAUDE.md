# Project

Elixir 1.20 on OTP 29. `lib/app/domain` holds pure logic; `lib/app/cli.ex` is the adapter and `lib/app/main.ex` only wires the process streams and exits.

- `scripts/setup` checks Elixir, fetches the locked deps and builds the Dialyzer PLT.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, `mix format`, compile with warnings as errors (including the type checker and Boundary), `mix credo --strict`, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% line coverage, Dialyzer and dependency audits.

Boundary enforces layers at compile time: `App.Domain` depends on nothing, `App.Cli` on `App.Domain`. A Credo guard keeps I/O, the clock, randomness and processes out of the domain, and all output goes through an injected device, never `IO.puts/1`. Every public function has a `@spec`. Return `{:ok, value}` or `{:error, reason}` from functions that can fail, as `Money.parse/1` does.

You cannot edit `mix.exs`, `mix.lock`, `.credo.exs`, `.formatter.exs`, `.tool-versions` or anything in `tools/guard`. If you need a dependency, say which one and why in your final message.
