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
- Do not pre-spawn helper subagents at loop start.
- Create helper subagents lazily, only when a step or repair actually needs one.
- Keep at most one live `$do-optimize-step` worker and at most one live `$fix-optimize-loop` worker at a time.
- Give each helper a fixed 15-minute wall-clock lease from spawn time.
- Reuse a helper only while it is healthy, still within its lease, and there is more work for that same role.
- Close a helper as soon as that role goes idle, and always close it when its lease expires.
- The coordinator owns:
  - the infinite loop
  - experiment execution
  - polling and timeout handling
  - raw metric extraction
  - delegating subagents
  - helper-subagent reuse and recovery
  - helper-subagent lease tracking and cleanup
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
2. Start with no helper subagents. Track optional helper slots for:
   - one `$do-optimize-step` worker
   - one `$fix-optimize-loop` worker
   Each slot should also track the helper's spawn time so you can enforce the 15-minute lease.
3. If `pending.experiment_command` is empty, ensure a healthy leased `$do-optimize-step` worker exists, send input to it, wait for it, then clean it up if the role is idle or its lease is over.
4. Run `pending.experiment_command`, redirecting all output to `.optimize/<DATETIME>/optimization_runs/step_####.log`.
5. Poll until the experiment finishes or `pending.timeout_seconds` elapses.
6. Update `last_run` in the state file with the raw outcome:
   - `outcome=completed` when the command exits successfully and the metric parses
   - `outcome=parse_error` when the command exits successfully but the metric does not parse
   - `outcome=crash` when the command exits non-zero
   - `outcome=timeout` when the timeout is exceeded
7. Write any raw error details into `last_error`.
8. Ensure a healthy leased `$do-optimize-step` worker exists, send input to it, and wait for it.
9. If the coordinator, the parser, the graph update flow, the repo recovery flow, or the subagent handoff breaks, ensure a healthy leased `$fix-optimize-loop` worker exists, send input to it, and wait for it.
10. After helper work finishes:
   - close any helper whose role is idle
   - close any helper whose 15-minute lease has expired
11. If a repair worker ran and exits:
   - if `pending.experiment_command` is valid, continue to the next run
   - if `pending.experiment_command` is empty, send input to `$do-optimize-step` again
12. Repeat forever.

If a helper exits, fails, becomes unusable, or ages out of its lease, close it, clear that slot, and create a fresh helper only when that role is needed again.

Subagent completions do not transfer control. The optimize coordinator always resumes after each `wait`.

## Subagent Contracts

Use worker subagents for both helper skills.

- The parent optimize coordinator must remain the single owner of the loop across every iteration.
- The parent optimize coordinator should normally keep zero live helpers until work actually requires one.
- At most one step worker and one repair worker may be live at the same time.
- Each helper gets a fixed 15-minute lease from spawn time.
- Reuse a helper only within that lease and only while that role is actively being used.
- Close helpers promptly when their role goes idle instead of keeping them around speculatively.
- If a helper has exited, expired, or become unusable, replace it only when that role is needed again.

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
- Reuse the worker only while its 15-minute lease is still active and the step role is still busy; otherwise close it.

For `$fix-optimize-loop`:

- Give the subagent ownership of:
  - `.optimize/<DATETIME>/optimization_loop_state.json`
  - the relevant failing code or config
  - loop support files in `$do-optimize-step/scripts/` when relevant
- Tell it to diagnose the bug, repair the loop or experiment setup, make the state file consistent again, and exit.
- Tell it explicitly that it is repairing one problem for the parent optimize coordinator, not taking over the loop.
- Reuse the worker only while its 15-minute lease is still active and repair work is still ongoing; otherwise close it.

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
- Do not keep idle helpers alive across long experiment runs just in case they are needed later.
- If parsing is ambiguous, repair the parser instead of guessing.
- If graph or Markdown generation breaks, repair it instead of abandoning the artifact.
- Never let one broken experiment terminate the overall loop.
- Never let a helper subagent become the loop owner. The optimize coordinator always resumes control after helper work finishes.
