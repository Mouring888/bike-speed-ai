---
name: team-run
description: Run a task end-to-end with the agent team (lead → researcher → builder → reviewer/verifier). Invoke as /team-run <task> for any non-trivial goal.
---

# team-run

Task: $ARGUMENTS

1. Load the `harness` skill; read `.harness/memory.md` and `.harness/state.md` (create `.harness/` if missing).
2. **Frame**: goal, done-criteria, constraints. If `state.md` already holds a task, resume it instead.
3. **Research** (only if facts are missing): spawn `researcher` with a precise question; wait for sources.
4. **Plan**: write the checklist to `.harness/state.md`.
5. **Build**: spawn `builder` per independent slice (parallel, worktree isolation if they touch code). UI/media slices go to `designer`.
6. **Check** in parallel: `reviewer` on the diff, `verifier` running the real checks.
7. Fix what they find (builder), re-verify. Loop until verifier passes or a real blocker is reached.
8. **Record**: lessons → `memory.md`; run summary → `log.md`; mark `state.md` done.
9. **Report**: outcome, evidence, what wasn't verified, next steps. No commit/push unless asked.
