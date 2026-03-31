---
name: "batch"
description: "Break a large task into a concrete multi-part plan and orchestrate parallel sub-agents for the independent parts. Use only when the user explicitly asks for delegation, sub-agents, or parallel agent work, or explicitly invokes $batch."
---

# Batch

Use this skill when the user wants a large task split into parallel workstreams.

## Do This First

- Read `references/orchestration-rubric.md`.
- Confirm this is an allowed delegation case:
  - the user explicitly asked for sub-agents, delegation, or parallel agent work
  - or the user explicitly invoked `$batch`
- If that condition is not true, do not use this skill.

## Workflow

1. Build a local plan before spawning anything.
   - Understand the whole task first.
   - Identify the immediate blocking step on the critical path.
   - Decide what work you should do locally right now.
2. Split the work into independent tracks.
   - Separate critical-path work from sidecar work.
   - Prefer delegation for concrete, bounded subtasks that can proceed independently.
   - Keep write scopes disjoint when code changes are involved.
3. Spawn multiple agents in parallel only for the independent tracks.
   - Give each agent a specific objective, ownership boundary, and expected output.
   - Tell code-editing workers they are not alone in the codebase and must not revert others' changes.
   - Use smaller/faster agents for straightforward subtasks.
4. Keep moving locally while agents run.
   - Do not stop and wait by reflex.
   - Advance the critical path yourself when possible.
   - Avoid duplicating delegated work.
5. Integrate deliberately.
   - Wait only when a returned result is now required.
   - Review delegated outputs quickly, then integrate or refine them.
   - Reconcile overlaps, run validation, and close no-longer-needed agents.

## What Good Batch Plans Look Like

- A small number of meaningful workstreams, not dozens of tiny tasks.
- Explicit ownership for each delegated slice.
- Clear outputs:
  - files to change
  - questions to answer
  - verification to perform
- One in-progress local step and several non-blocking delegated steps.

## Guardrails

- Do not delegate the immediate blocker if your very next step depends on it.
- Do not spawn agents for vague exploration when a direct local read would be faster.
- Do not create overlapping write ownership unless there is no cleaner decomposition.
- Do not keep waiting on agents in a loop when there is useful local work left.
- Do not use delegation to hide weak planning. Plan first, then parallelize.

## Output Expectations

- Start with a concise multi-part plan.
- Run the independent parts in parallel.
- Report progress in terms of workstreams and integration status, not per-agent chatter.
- Finish with an integrated result, remaining risks, and what was validated.
