# Working with Claude in an unslop project

## 1. Specify before building

Run `/unslop:spec`. Claude interviews you until the goal, inputs, outputs, data, errors, limits and non-goals are concrete, then writes `SPEC.md` with numbered acceptance criteria (`AC-1`, `AC-2`), each checkable by one automated test. Open questions stay listed until you answer them. Nothing gets built before you approve the spec.

Architectural choices the spec forces go into `docs/decisions/` as new MADR records with status `proposed`. Each has a Confirmation line naming the check that enforces it. Claude can add records but not edit existing ones; you accept a record by merging the pull request that adds it.

## 2. Build one criterion at a time

For each criterion Claude:

1. writes the failing test and shows it failing,
2. implements until `scripts/fast-check` passes (`unslop check` in an adopted repository; Claude's end-of-turn check is `unslop check --fast`, and CI runs the tests),
3. asks the `reviewer` agent to review the changed files against the spec and decision record 0003,
4. fixes anything the reviewer blocks, then commits.

To stop Claude from touching tests while it implements, run `touch .claude/tests.locked` yourself. Delete the file when new tests should be written.

## 3. Long unattended runs

Claude cannot measure wall-clock hours, so "work for four hours" gives it nothing to check. Give it an exit condition instead. Run `/unslop:long-run`; it writes `feature_list.json` (one entry per criterion with `passes: false`) and `progress.md`, then gives you a condition to start with:

```text
/goal scripts/fast-check (or unslop check) exits 0 with its output shown in the transcript, every entry in feature_list.json has "passes": true with a named test confirmed by the reviewer subagent, and git diff --name-only --diff-filter=DM origin/main shows no changed or deleted test files; or stop after 150 turns
```

`/goal` checks the condition after every turn. The end-of-session check refuses to let a turn end on a failing `fast-check`, and ends the session visibly after three identical failures. State lives in files and commits, so a compacted or fresh context resumes where the last one stopped.

For a headless run inside a dev container:

```bash
claude -p "/goal <same condition>" --permission-mode auto --max-turns 400 --max-budget-usd 60 --output-format stream-json --verbose
```

## 4. When a guardrail blocks Claude

Claude cannot edit lint or type configs, CI, `scripts/`, `CLAUDE.md` or decision records. When it needs a change there (a rule exception, a new script), it says what and why in its final message. You make the change yourself in a pull request, which CI and the ruleset then check.

In an adopted repository Claude can add or update dependencies itself. Minor and patch updates pass on their own; a new package, a major version or a build-file change needs the `unslop-reviewed` label, which you add after reading what the job summary lists. If later commits change those files again, CI removes the label. Template projects keep dependency files read-only.

When a change reaches 40 lines, Claude is asked to run the reviewer agent before it finishes. Its findings show up in the conversation; read them, since a model review can be wrong in both directions.

If a pull request intentionally changes existing tests, add the `tests-reviewed` label so CI accepts it.

To see which guardrails get in the way, run `unslop stats --labels 30` after a week or two. It counts each rule's blocks in the repository and shows recent examples, so you can tell real catches from noise.

## 5. Merging

Push the branch and open a pull request. The `verify` job runs the same scripts plus mutation testing and a vulnerability audit. The ruleset blocks merging until it passes, and blocks force pushes to `main`.
