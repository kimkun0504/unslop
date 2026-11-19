# Working rules

Hooks, linters, type checkers and CI enforce the standards. These lines cover only what tools cannot check.

- No code comments in any language. Names, types and small functions carry the meaning. Decisions that need prose go in `docs/decisions/`.
- Before writing code for a feature, confirm the spec has acceptance criteria. If anything is ambiguous, ask instead of guessing.
- Copy the patterns of the closest existing feature. Never introduce a second way of doing something that already has one.
- Write the failing test first, show it failing, then implement. Never edit, skip or delete an existing test to get green.
- When a check fails, fix the cause. Never weaken a type, lint rule, threshold or config. If a guardrail blocks you, explain what change you need in your final message.
- Done means the project check passes with its output shown (`unslop check`, or `scripts/fast-check` in a project made from a template), the reviewer subagent found no blocking issue, and every acceptance criterion names the test that proves it.
- Long tasks: keep state in `feature_list.json` and `progress.md`, commit after each passing feature, and keep going until the goal condition holds. Your context will be compacted automatically, so never stop early to save context.
- Never run infrastructure, cluster or database mutations. Plan, then hand the plan to the human.
