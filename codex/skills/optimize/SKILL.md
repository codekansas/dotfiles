---
name: "optimize"
description: "Use when the user provides natural-language instructions for what to optimize (for example ML loss, latency, or CUDA benchmark runtime) and wants a forever optimization loop. Infer the experiment setup from the codebase, write `optimization_results_<metric>.md` first with a consistent metric collection protocol, then iterate indefinitely until the user stops it."
---

## Input Contract

- The user only needs to provide natural-language optimization intent.
- Example inputs:
  - "Optimize training loss for this model."
  - "Minimize CUDA kernel runtime for this benchmark."
  - "Improve p95 latency for this service benchmark."
- If direction is not explicit, default to `minimize`.

## Inference-First Setup

Before running optimization steps, infer a reproducible experiment from repository context.

1. Read codebase signals:
   - `README`, benchmark scripts, training scripts, test harnesses, `Makefile`, package scripts, CI commands.
2. Infer and lock the metric protocol:
   - `metric` name (snake case for filename)
   - `direction` (`minimize` or `maximize`)
   - `eval_command` (one reproducible evaluation run)
   - `metric_parser` rule for extracting one numeric metric value
   - fixed conditions (seed, dataset split, batch size, device, warmup/repeats)
3. Validate consistency:
   - Run `eval_command` at least once and confirm the parser yields a numeric value.
   - If parsing is ambiguous, refine the parser before continuing.

## Output File Contract

- Always write `optimization_results_<metric>.md` in the working directory.
- Create this file before step 1 is recorded.
- The top of the file must define the metric protocol used for all subsequent steps.
- Keep a results table below the protocol.
- Keep a running optimization idea log after the table.

Use this layout:

```markdown
# Optimization Results: <metric>

Direction: <minimize|maximize>
Started: <UTC timestamp>

## Metric Protocol (Authoritative)

- Objective: <natural-language objective>
- Eval command: `<exact command>`
- Metric parser: <regex/parser rule>
- Value semantics: <unit, aggregation, lower-is-better or higher-is-better>
- Fixed conditions: <seed/device/dataset/warmup/repeats>

| step | timestamp_utc | metric_value | best_value | delta_vs_best | status | notes | metadata |
|---:|---|---:|---:|---:|---|---|---|
| 1 | 2026-03-03T10:00:00Z | 0.1234 | 0.1234 | 0.0000 | baseline | initial measurement | sha=abc123; cfg=config.yaml |

## Idea Log (Running)

- [ ] Step 2 candidate: <idea>
- [ ] Step 3 candidate: <idea>
```

## Infinite Optimization Workflow

1. Infer experiment setup from codebase context and write `optimization_results_<metric>.md` with the full metric protocol section.
2. Run baseline (step 1):
   - Execute `eval_command`.
   - Parse metric via the protocol.
   - Record step 1 in the table and set `best_value`.
3. Enter an unbounded optimization loop:
   - Choose next idea from the running log.
   - Apply code/config changes.
   - Run `eval_command` once per step.
   - Parse metric and update `best_value` and `delta_vs_best`.
   - Append a row for that step with notes and metadata.
   - Update idea log with what was tried, observed effect, and next candidates.
   - Continue forever.
4. Stop condition:
   - Only stop when the user explicitly interrupts/kills the run.
   - On interruption, keep the file intact and add a final note with the last completed step.

## Reliability Rules

- Prefer long-running sessions (`tmux`/`screen`) for overnight/multi-day optimization.
- Do not change the metric protocol silently mid-run; if it must change, record a protocol change note in the file before continuing.
- If a step fails (command error, parse failure, environment issue), write a row with `status=error`, include notes, and continue unless unrecoverable.
- Never skip recording attempted steps.
- Do not terminate just because progress stalls; continue proposing and testing ideas until stopped by the user.
