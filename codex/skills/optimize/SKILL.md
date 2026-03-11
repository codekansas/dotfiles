---
name: "optimize"
description: "Use when the user provides natural-language instructions for what to optimize and wants an autonomous optimization loop that keeps running until interrupted. The current Codex agent stays alive, runs experiments itself, and delegates bounded step work to $do-optimize-step and loop repairs to $fix-optimize-loop."
---

## Input Contract

- The user only needs to provide natural-language optimization intent.
- Example inputs:
  - "Optimize training loss for this model."
  - "Minimize CUDA kernel runtime for this benchmark."
  - "Improve p95 latency for this service benchmark."
- If direction is not explicit, default to `minimize`.

## Termination Policy

- Once the optimization loop begins, `LOOP FOREVER`.
- `NEVER PAUSE` between iterations unless the human explicitly interrupts or an external blocker truly requires the human.
- Do not stop because progress is slow, the results are mixed, or you need to think harder.
- Do not stop after one success, one failure, a handful of failures, or a long quiet period.
- Do not ask the human whether you should continue. Silence means continue.
- Do not wait around for confirmation after a run, after a repair, or after a new best result. Finish one step and immediately start the next one.
- Do not treat "good enough for now" as a valid stopping point.
- Treat unplanned idleness as a serious failure mode:
  - on ML workloads, a paused loop can leave expensive GPUs idle while no experiments are running, wasting real money
  - on deadline-driven projects, a paused loop can burn entire nights or weekends while the human is asleep, causing serious schedule slips
  - the user may have started the loop specifically so work continues unattended, so stopping early defeats the point of the skill
- Only stop for one of these reasons:
  - the human explicitly interrupts or redirects you
  - an external blocker requires the human, such as missing credentials, unavailable hardware, or a hard safety boundary
- If a bug appears anywhere in the loop, call `$fix-optimize-loop`, repair it, and continue.
- If you ever find yourself thinking "I should pause here" or "this is a good stopping point", that is usually a sign you should continue instead.

## Coordinator Model

- The current Codex agent is the long-running coordinator.
- Never hand off ownership of the optimization loop to a subagent.
- Subagents are bounded helpers. They do work for one step, then return control immediately to the parent optimize coordinator.
- Create exactly two helper subagents and reuse them throughout the run:
  - one dedicated `$do-optimize-step` worker
  - one dedicated `$fix-optimize-loop` worker
- Do not spawn fresh helper subagents for routine iterations.
- The coordinator owns:
  - the infinite loop
  - experiment execution
  - polling and timeout handling
  - raw metric extraction
  - delegating subagents
  - helper-subagent reuse and recovery
- The coordinator should stay lightweight.
- The coordinator should not do the deep experiment analysis itself.
- After each run, delegate the experiment analysis, results updates, and next experiment implementation to a subagent using `$do-optimize-step`.
- Whenever the loop itself breaks, delegate the repair to a subagent using `$fix-optimize-loop`.
- The coordinator remains responsible for deciding when to run the next experiment, when to call helpers, and when the overall loop continues.
- The coordinator must immediately resume the loop after each helper returns; helper completion is a trigger to continue, not a reason to pause.

## Loop Artifacts

- At loop start, create a timestamped run directory at `.optimize/<DATETIME>/`.
- Write the run's state and derived artifacts inside that directory:
  - `.optimize/<DATETIME>/optimization_loop_state.json`
  - `.optimize/<DATETIME>/optimization_results_<metric>.md`
  - `.optimize/<DATETIME>/optimization_results_<metric>.tsv`
  - `.optimize/<DATETIME>/optimization_progress_<metric>.svg`
  - `.optimize/<DATETIME>/optimization_runs/step_####.log`
- `$do-optimize-step` owns the artifact helper scripts in its own `scripts/` directory.

Use this exact TSV header:

```tsv
step	timestamp_utc	metric_value	best_value	delta_vs_best	decision	hypothesis	evidence	metadata
```

Field rules:

- `decision` must be one of `baseline`, `keep`, `discard`, or `error`.
- `metric_value` must be numeric when parsing succeeds; leave it blank for hard failures.
- `best_value` is the best metric observed after that step.
- `delta_vs_best` should be `metric_value - best_value` for `minimize` objectives and `best_value - metric_value` for `maximize` objectives.

## State Contract

Use `.optimize/<DATETIME>/optimization_loop_state.json` as the coordinator-to-subagent handoff file. It must stay valid JSON and include, at minimum, these fields:

```json
{
  "objective": "minimize validation bpb",
  "started_at_utc": "2026-03-11T08:00:00Z",
  "metric": "val_bpb",
  "direction": "minimize",
  "eval_command": "uv run train.py",
  "profile_command": "grep '^val_bpb:' .optimize/20260311T080000Z/optimization_runs/step_0001.log",
  "metric_pattern": "^val_bpb:\\s*([0-9.]+)$",
  "metric_group": 1,
  "fixed_conditions": "dataset=fixed, device=cuda, seed=1337",
  "value_semantics": "validation BPB, lower is better",
  "run_dir": ".optimize/20260311T080000Z",
  "state_path": ".optimize/20260311T080000Z/optimization_loop_state.json",
  "results_markdown": ".optimize/20260311T080000Z/optimization_results_val_bpb.md",
  "results_tsv": ".optimize/20260311T080000Z/optimization_results_val_bpb.tsv",
  "results_graph": ".optimize/20260311T080000Z/optimization_progress_val_bpb.svg",
  "runs_dir": ".optimize/20260311T080000Z/optimization_runs",
  "current_step": 1,
  "best_value": null,
  "best_reference": "",
  "last_error": "",
  "last_run": {
    "step": 0,
    "completed_at_utc": "",
    "outcome": "",
    "metric_value": null,
    "return_code": 0,
    "timed_out": false,
    "log_path": "",
    "hypothesis": "",
    "evidence": "",
    "metadata": "",
    "candidate_reference": ""
  },
  "pending": {
    "hypothesis": "establish baseline",
    "evidence": "no prior runs",
    "metadata": "baseline",
    "experiment_command": "uv run train.py",
    "timeout_seconds": 600
  }
}
```

Notes:

- `last_run` is the raw output of the most recent experiment.
- `pending` is the next experiment the coordinator should run.
- `run_dir` is the timestamped output directory for the current optimize session.
- `state_path` should normally point at `.optimize/<DATETIME>/optimization_loop_state.json`.
- `best_reference` and `last_run.candidate_reference` may be commit hashes, branch names, or another loop-owned checkpoint identifier.

## Coordinator Loop

The long-running coordinator should use this loop:

1. Initialize or reuse `.optimize/<DATETIME>/optimization_loop_state.json`.
2. Spawn or reuse exactly two helper subagents:
   - a dedicated experiment-step worker for `$do-optimize-step`
   - a dedicated repair worker for `$fix-optimize-loop`
3. Reuse those same helper subagents with new input across the entire optimization run.
4. If `pending.experiment_command` is empty, send input to the existing `$do-optimize-step` worker, wait for it, then continue.
5. Run `pending.experiment_command`, redirecting all output to `.optimize/<DATETIME>/optimization_runs/step_####.log`.
6. Poll until the experiment finishes or `pending.timeout_seconds` elapses.
7. Update `last_run` in the state file with the raw outcome:
   - `outcome=completed` when the command exits successfully and the metric parses
   - `outcome=parse_error` when the command exits successfully but the metric does not parse
   - `outcome=crash` when the command exits non-zero
   - `outcome=timeout` when the timeout is exceeded
8. Write any raw error details into `last_error`.
9. Send input to the existing `$do-optimize-step` worker and wait for it.
10. If the coordinator, the parser, the graph update flow, the repo recovery flow, or the subagent handoff breaks, send input to the existing `$fix-optimize-loop` worker and wait for it.
11. After the repair worker exits:
   - if `pending.experiment_command` is valid, continue to the next run
   - if `pending.experiment_command` is empty, send input to `$do-optimize-step` again
12. Repeat forever.

If one of the two helper subagents exits, fails, or becomes unusable, recreate that same helper role and continue. Recreating a broken helper is allowed; spawning fresh helpers for every loop iteration is not.

Subagent completions do not transfer control. The optimize coordinator always resumes after each `wait`.

## Subagent Contracts

Use worker subagents for both helper skills.

- The parent optimize coordinator must remain the single owner of the loop across every iteration.
- The parent optimize coordinator should normally keep exactly two helper agent IDs live at once: one step worker and one repair worker.
- Reuse those helper agent IDs with new input instead of spawning new helpers for ordinary loop work.
- Only create a replacement helper when one of the two dedicated helpers has actually failed, exited, or become unusable.

For `$do-optimize-step`:

- Give the subagent ownership of:
  - `.optimize/<DATETIME>/optimization_loop_state.json`
  - `.optimize/<DATETIME>/optimization_results_<metric>.md`
  - `.optimize/<DATETIME>/optimization_results_<metric>.tsv`
  - `.optimize/<DATETIME>/optimization_progress_<metric>.svg`
  - the code changes for the next experiment
- Tell it to read the repo, the state file, the existing results, and the most recent run log.
- Tell it to summarize the last experiment, update the TSV/Markdown/SVG artifacts, decide keep or discard, restore the best kept state if needed, implement the next experiment, update `pending`, and exit.
- Tell it explicitly that it does not own the loop and must return control to the parent optimize coordinator.
- Reuse this same worker for later experiment-step messages.

For `$fix-optimize-loop`:

- Give the subagent ownership of:
  - `.optimize/<DATETIME>/optimization_loop_state.json`
  - the relevant failing code or config
  - loop support files in `$do-optimize-step/scripts/` when relevant
- Tell it to diagnose the bug, repair the loop or experiment setup, make the state file consistent again, and exit.
- Tell it explicitly that it is repairing one problem for the parent optimize coordinator, not taking over the loop.
- Reuse this same worker for later repair messages.

Because the coordinator is blocked on these results, it should `wait` for each subagent before proceeding.

## Results Requirements

The coordinator must keep these artifacts current across the loop:

- A TSV ledger with one row per completed attempt.
- A Markdown summary that includes:
  - objective, direction, and start time
  - metric protocol
  - observability protocol
  - current best value
  - last run summary
  - the full TSV rendered as Markdown
  - the pending experiment summary
- An SVG graph that shows:
  - discarded attempts as faint gray dots
  - baseline and kept improvements as green markers
  - the running best as a green step line
  - short labels on kept improvements
  - the metric direction in the Y-axis label

## Reliability Rules

- The first run must establish the baseline.
- Keep experiment execution isolated from experiment design. The coordinator runs experiments; `$do-optimize-step` decides what to try next.
- If a subagent fails, that is not a stopping condition. Call `$fix-optimize-loop` and continue.
- If parsing is ambiguous, repair the parser instead of guessing.
- If graph or Markdown generation breaks, repair it instead of abandoning the artifact.
- Never let one broken experiment terminate the overall loop.
- Never let a helper subagent become the loop owner. The optimize coordinator always resumes control after helper work finishes.
