---
status: accepted
date: 2026-11-18
decision-makers: Kun Kim
---

# No code comments

## Context and Problem Statement

Agents copy whatever the codebase shows. Comments drift from the code, excuse workarounds, and teach the next change to add more of both.

## Decision Outcome

Source files contain no comments. Meaning lives in names, types, small functions and tests. Prose that explains a decision lives in this folder.

Allowed exceptions, each enforced by the checker's allowlist rather than by judgment:

- A shebang line.
- Tool directives that change behavior and have no other syntax: Go `//go:` directives, `/// <reference>` in TypeScript declaration files, Python encoding declarations.
- Generated files carrying the standard generated-code marker.

Suppression directives (`eslint-disable`, `@ts-expect-error`, `//nolint`, `# noqa`, `# type: ignore`, `@Suppress`) are not exceptions. They are banned separately.

### Confirmation

The language's no-comments checker runs in `scripts/fast-check`, in the Stop gate and in CI. A comment fails the build.
