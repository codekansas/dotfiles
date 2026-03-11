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
- Do not stop because progress is slow, the results are mixed, or you need to think harder.
- Do not stop after one success, one failure, a handful of failures, or a long quiet period.
- Do not ask the human whether you should continue. Silence means continue.
- Do not treat "good enough for now" as a valid stopping point.
- Only stop for one of these reasons:
  - the human explicitly interrupts or redirects you
  - an external blocker requires the human, such as missing credentials, unavailable hardware, or a hard safety boundary
- If a bug appears anywhere in the loop, call `$fix-optimize-loop`, repair it, and continue.

## Coordinator Model

- The current Codex agent is the long-running coordinator.
- The coordinator owns:
  - the infinite loop
  - experiment execution
  - polling and timeout handling
  - raw metric extraction
  - delegating subagents
- The coordinator should stay lightweight.
- The coordinator should not do the deep experiment analysis itself.
- After each run, delegate the experiment analysis, results updates, and next experiment implementation to a subagent using `$do-optimize-step`.
- Whenever the loop itself breaks, delegate the repair to a subagent using `$fix-optimize-loop`.

## Loop Artifacts

- Keep `optimization_loop_state.json` in the target working directory root.
- At loop start, create a timestamped run directory at `.optimize/<DATETIME>/`.
- Write the run's derived artifacts inside that directory:
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

Use `optimization_loop_state.json` as the coordinator-to-subagent handoff file. It must stay valid JSON and include, at minimum, these fields:

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
- `best_reference` and `last_run.candidate_reference` may be commit hashes, branch names, or another loop-owned checkpoint identifier.

## Coordinator Loop

The long-running coordinator should use this loop:

1. Initialize or reuse `optimization_loop_state.json`.
2. If `pending.experiment_command` is empty, spawn a worker subagent with `$do-optimize-step`, wait for it, then continue.
3. Run `pending.experiment_command`, redirecting all output to `.optimize/<DATETIME>/optimization_runs/step_####.log`.
4. Poll until the experiment finishes or `pending.timeout_seconds` elapses.
5. Update `last_run` in the state file with the raw outcome:
   - `outcome=completed` when the command exits successfully and the metric parses
   - `outcome=parse_error` when the command exits successfully but the metric does not parse
   - `outcome=crash` when the command exits non-zero
   - `outcome=timeout` when the timeout is exceeded
6. Write any raw error details into `last_error`.
7. Spawn a worker subagent with `$do-optimize-step` and wait for it.
8. If the coordinator, the parser, the graph update flow, the repo recovery flow, or the subagent handoff breaks, spawn a worker subagent with `$fix-optimize-loop` and wait for it.
9. After the repair worker exits:
   - if `pending.experiment_command` is valid, continue to the next run
   - if `pending.experiment_command` is empty, call `$do-optimize-step` again
10. Repeat forever.

## Subagent Contracts

Use worker subagents for both helper skills.

For `$do-optimize-step`:

- Give the subagent ownership of:
  - `optimization_loop_state.json`
  - `optimization_results_<metric>.md`
  - `optimization_results_<metric>.tsv`
  - `optimization_progress_<metric>.svg`
  - the code changes for the next experiment
- Tell it to read the repo, the state file, the existing results, and the most recent run log.
- Tell it to summarize the last experiment, update the TSV/Markdown/SVG artifacts, decide keep or discard, restore the best kept state if needed, implement the next experiment, update `pending`, and exit.

For `$fix-optimize-loop`:

- Give the subagent ownership of:
  - `optimization_loop_state.json`
  - the relevant failing code or config
  - loop support files in `$do-optimize-step/scripts/` when relevant
- Tell it to diagnose the bug, repair the loop or experiment setup, make the state file consistent again, and exit.

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
