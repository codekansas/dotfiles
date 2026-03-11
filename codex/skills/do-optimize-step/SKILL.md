---
name: "do-optimize-step"
description: "Use when the optimize loop needs one bounded subagent step to process the most recent experiment and prepare the next one. Read .optimize/<DATETIME>/optimization_loop_state.json and prior artifacts, summarize the last run, update the TSV/Markdown/SVG outputs, decide keep or discard, implement the next experiment, update state, and exit."
---

## Purpose

- This is the bounded worker for the long-running `optimize` skill.
- It is invoked in a subagent for one step only.
- The parent optimize coordinator may reuse the same subagent thread for many separate step requests.
- It should not run the experiment command itself.
- It does not own the optimization loop and must return control to the parent optimize coordinator.

## Required Inputs

The parent optimize coordinator should provide:

- the target working directory
- the absolute path to `.optimize/<DATETIME>/optimization_loop_state.json`
- the path to the latest run log when one exists
- the current objective and metric protocol
- the timestamped `run_dir`, which should normally be `.optimize/<DATETIME>/`

## Responsibilities

1. Read `.optimize/<DATETIME>/optimization_loop_state.json`.
2. Read the existing results artifacts from the paths stored in state. These should normally live under `.optimize/<DATETIME>/`.
3. Read the relevant repository code before editing anything.
4. Process the most recent run recorded in `last_run`.
5. Update the results TSV, the Markdown summary, and the SVG graph.
6. Decide whether the last experiment should be kept, discarded, or marked as an error.
7. Restore the best kept state if the last experiment should not stay.
8. Implement exactly one next experiment.
9. Update `pending` in the state file and exit.

## Baseline Rule

- If there is no completed run yet, prepare the baseline experiment first.
- The baseline experiment should run the code as-is.
- In that case, write a valid `pending` block and exit without changing the code.

## Decision Rules

Use these decision values in the TSV:

- `baseline` for the very first successful run
- `keep` when the new result should become the new best state
- `discard` when the experiment ran but should not stay
- `error` when the experiment crashed, timed out, or did not yield a trustworthy metric

Primary objective:

- Optimize the tracked metric in the requested direction.

Simplicity criterion:

- All else equal, simpler is better.
- A tiny improvement that adds ugly complexity is often not worth keeping.
- Equal results with clearly simpler code are a keep.
- Small gains from removing code are especially strong keeps.

## Artifact Updates

When `last_run.step > 0`, this skill should:

1. Convert `last_run` into one TSV row.
2. Update `best_value` and `best_reference` when the decision is `baseline` or `keep`.
3. Rewrite the Markdown summary so it reflects the full run history and the next pending experiment by calling `scripts/update_optimization_markdown.py`.
4. Regenerate the SVG graph by calling `scripts/render_optimization_progress.py`.

That graph should make the history easy to scan:

- gray dots show discarded exploration without dominating the view
- green points show the runs that actually moved the frontier
- the running-best step line makes it obvious which changes helped and whether progress has flattened

## Repository State Rules

- If the last experiment is a `keep`, preserve that state as the new best baseline.
- If the last experiment is a `discard` or `error`, restore the codebase to the last kept state before implementing the next experiment.
- Only rewind loop-owned experiment changes.
- Do not disturb unrelated human edits.

## State Updates

Before exiting, ensure the state file is coherent:

- `current_step` should point to the next experiment to run.
- `last_error` should be cleared when the loop is healthy.
- `pending.hypothesis`, `pending.evidence`, `pending.metadata`, `pending.experiment_command`, and `pending.timeout_seconds` must all be valid.
- `pending.experiment_command` should be exactly what the parent optimize coordinator will run next.
- All artifact paths should continue to point at the current `.optimize/<DATETIME>/` run directory.

## Boundaries

- Do not run the experiment command.
- Do not turn into a long-running loop.
- Do not take ownership of the optimization loop.
- Do not spawn watchers, daemons, or nested coordinators.
- If you discover a bug in the optimization loop itself, leave the state consistent, return control, and let the parent coordinator call `$fix-optimize-loop`.
