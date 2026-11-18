---
name: unslop-spec
description: Interview the human and write SPEC.md with numbered, testable acceptance criteria before any code is written. Use at the start of a new project or a new feature.
---

# Write the spec before the code

1. Ask the human, in short batches, until each of these is concrete: the user and the problem, inputs and outputs, data that must persist, error cases, limits (scale, latency, security), and what is explicitly out of scope.
2. Never fill a gap with a guess. Each open question stays in an `Open questions` section until the human answers it.
3. Write SPEC.md with these sections: Goal, Users, Acceptance criteria, Data, Errors, Non-goals, Open questions.
4. Each acceptance criterion is numbered (`AC-1`, `AC-2`), observable from outside the code, and checkable by one automated test. Rewrite any criterion that says "fast", "clean", "robust" or "user-friendly" into a measurable one.
5. Record every architectural choice the spec forces as a decision in `docs/decisions/` using the existing template, with a Confirmation line naming the check that enforces it.
6. Show the spec to the human and wait for approval before writing code.
