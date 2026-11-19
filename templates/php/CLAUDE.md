# Project

PHP 8.5 with Composer. `src/Domain` holds pure logic: deptrac forbids it from depending on `src/Cli`, and PHPStan forbids I/O calls inside it. `src/Cli` is the adapter; `bin/app` only wires streams.

- `scripts/setup` checks PHP and Composer, then installs locked dependencies.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, PHP-CS-Fixer, PHPStan at max level with strict rules, deptrac, PHPUnit.
- `scripts/verify` is what CI runs: fast-check plus 100% coverage and `composer audit`.
- `scripts/mutation` runs Infection and must report 100% MSI.

Every file declares `strict_types`. Express types natively, not in docblocks: typed properties, enums, readonly classes, and variadic parameters (`string ...$lines`) instead of untyped arrays. Parse input into final readonly classes with private constructors, as `Money::parse` does. Write output through `Output`, never `echo` or `var_dump`.

You cannot edit `composer.json`, the lockfile or any tool config. If you need a package, say which one and why in your final message.
