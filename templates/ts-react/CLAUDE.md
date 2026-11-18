# Project

React 19, TypeScript 6 (strictest), Vite, Tailwind 4, Vitest, pnpm. Features live in `src/features/<name>/` with `domain/` (pure logic, no React) and `ui/` (components). `src/app` composes features. The boundaries lint rule enforces this direction.

- `scripts/setup` installs the locked dependencies.
- `scripts/fast-check` must pass before you stop: types, lint, format, suppressions, tests.
- `scripts/verify` is what CI runs: fast-check plus 100% coverage, unused-code detection and a production build.
- `scripts/mutation` must report a 100% mutation score.

Parse input into domain types that cannot hold invalid values, as `Money.parse` does; return `Parsed<T>` instead of throwing. Style only with the design tokens in `src/styles.css`. Use named exports. Test through the accessible role or label, as the user would.

You cannot edit `package.json`, the lockfile or any config. If you need a dependency, say which one and why in your final message.
