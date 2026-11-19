---
name: long-run
description: Set up and run a multi-hour autonomous build in an unslop project with a feature list, progress file and a /goal exit condition. Use when asked to keep working for hours or to finish a whole spec unattended.
---

# Long autonomous run

Time is not a stopping rule. The run ends when a checkable condition holds.

The project check is `scripts/fast-check` in a project made from a template. In a repository with `unslop.toml`, it is the `unslop check` command the session context names; use that wherever this skill says `scripts/fast-check`.

1. Read SPEC.md. If it lacks numbered acceptance criteria, stop and ask the human for them.
2. Write `feature_list.json`: one entry per acceptance criterion with `id`, `criterion`, `test` (the test that proves it, empty for now) and `passes: false`. Commit it.
3. Write `progress.md` with the current state and the next feature. Update it after every feature so a fresh context can resume.
4. For each feature in order: write the failing test, run it and show the failure, implement, run `scripts/fast-check`, ask the `reviewer` subagent with the changed files, fix anything it blocks, set `passes: true` with the test name, commit.
5. Never mark `passes: true` without the test name and a reviewer `VERDICT: PASS` in the transcript.

Tell the human to start the run with:

```text
/goal scripts/fast-check exits 0 with its output shown in the transcript, every entry in feature_list.json has "passes": true with a named test confirmed by the reviewer subagent, and git diff --name-only --diff-filter=DM origin/main shows no changed or deleted test files; or stop after 150 turns
```

Headless, inside a dev container:

```bash
claude -p "/goal <same condition>" --permission-mode auto --max-turns 400 --max-budget-usd 60 --output-format stream-json --verbose
```

Before a long run, the human can lock tests for the implementation phase with `touch .claude/tests.locked`.
