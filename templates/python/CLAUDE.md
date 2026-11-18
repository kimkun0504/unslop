# Project

Python 3.13 with uv and a src layout. Layers run one way: `app.api` calls `app.service` calls `app.domain`. The domain does no I/O.

- `scripts/setup` installs the locked dependencies.
- `scripts/fast-check` must pass before you stop: format, lint, types, no comments, import layers, suppressions, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% branch coverage and dependency hygiene.
- `scripts/mutation` must report every mutant killed.

Parse raw input into domain types at the boundary, as `Money.parse` does. Errors are exception classes that build their own message. Write output to injected streams, never `print`.

You cannot edit `pyproject.toml` or `uv.lock`. If you need a dependency, say which one and why in your final message.
