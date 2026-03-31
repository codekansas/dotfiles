# Orchestration Rubric

Use this rubric to turn a large task into a parallel agent plan without creating chaos.

## 1. Plan Before Delegation

Always decide these locally first:

- What is the actual end state?
- What is the immediate blocker on the critical path?
- What can proceed independently in parallel?
- What should remain local because it is tightly coupled or urgent?

If you cannot answer those, do not spawn agents yet.

## 2. Prefer Bounded Subtasks

Good delegated tasks are:

- concrete
- independently completable
- materially useful
- easy to verify

Examples:

- inspect a specific subsystem and answer one question
- patch a single module or file family
- run verification for a specific risk area

Bad delegated tasks are:

- "understand the whole codebase"
- "figure out what to do"
- "work on whatever seems useful"

## 3. Design Write Ownership

For coding tasks, assign ownership explicitly:

- which files or directories the worker owns
- whether the worker is read-only or editing
- what final artifact is expected

When multiple workers edit code, keep write scopes disjoint whenever possible.

## 4. Keep The Main Agent Moving

After delegation:

- continue local critical-path work
- inspect relevant code
- prepare integration points
- avoid repeating delegated work

Wait only when a sub-agent result is now needed to continue.

## 5. Integrate And Verify

When workers finish:

- review the returned output quickly
- integrate without undoing unrelated work
- run focused validation for the affected areas
- close agents that are no longer needed

## 6. Delegation Trigger Discipline

This skill should only be used when delegation is explicitly permitted by the user request.
Big task size alone is not enough.
