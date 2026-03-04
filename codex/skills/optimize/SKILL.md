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

## Inference-First Setup (Observability First)

Before running optimization steps, infer a reproducible experiment from repository context.

1. Read codebase signals:
   - `README`, benchmark scripts, training scripts, test harnesses, `Makefile`, package scripts, CI commands.
2. Define observability before optimization:
   - Identify the likely hot path and its owning files/functions.
   - Add or enable toggleable profiling/logging (CLI flag, env var, config switch) so diagnostics can be turned on for analysis and off for fast iteration.
   - Record one reproducible diagnostics command (`profile_command`) and how to collect artifacts (stdout logs, trace files, profiler summaries).
   - CUDA-specific minimum when relevant: kernel names, launch config (grid/block), per-kernel runtime, occupancy, memory throughput/transactions, and sync/transfer costs.
3. Infer and lock the metric protocol:
   - `metric` name (snake case for filename)
   - `direction` (`minimize` or `maximize`)
   - `eval_command` (one reproducible evaluation run)
   - `metric_parser` rule for extracting one numeric metric value
   - fixed conditions (seed, dataset split, batch size, device, warmup/repeats)
4. Validate consistency:
   - Run `eval_command` at least once and confirm the parser yields a numeric value.
   - Run `profile_command` at least once and confirm diagnostics are actually emitted.
   - If parsing is ambiguous, refine the parser before continuing.
   - If observability is missing or low-signal, implement instrumentation first and record that as the first optimization step.

## Output File Contract

- Always write `optimization_results_<metric>.md` in the working directory.
- Create this file before step 1 is recorded.
- The top of the file must define the metric protocol used for all subsequent steps.
- Include an observability protocol section so each idea can be justified by code-local evidence.
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

## Observability Protocol (Authoritative)

- Profile command: `<exact command>`
- Toggle: `<flag/env/config that enables profiling>`
- Artifacts: <where logs/traces are written>
- Key diagnostics: <fields that explain bottlenecks>
- Code hotspots: <files/functions mapped to diagnostics>

| step | timestamp_utc | metric_value | best_value | delta_vs_best | status | hypothesis | evidence | metadata |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 | 2026-03-03T10:00:00Z | 0.1234 | 0.1234 | 0.0000 | baseline | establish control | profiler shows kernel_x dominates 62% runtime | sha=abc123; cfg=config.yaml |

## Idea Log (Running)

- [ ] Step 2 candidate: <idea>
  - Hypothesis: <why this should help>
  - Evidence link: <profiling/log lines + code location>
- [ ] Step 3 candidate: <idea>
  - Hypothesis: <why this should help>
  - Evidence link: <profiling/log lines + code location>
```

## Infinite Optimization Workflow

1. Infer experiment setup from codebase context and write `optimization_results_<metric>.md` with both metric and observability protocols.
2. Establish observability (record this as step 1 when you need to add instrumentation):
   - Add/enable toggleable diagnostics with minimal default overhead.
   - Capture a profiling/logging snapshot and map top bottlenecks to concrete code locations.
3. Run baseline:
   - Execute `eval_command`.
   - Execute `profile_command` when gathering evidence for idea generation.
   - Parse metric via the protocol.
   - Record the baseline row as the next step number and initialize `best_value` from that row.
4. Enter an unbounded optimization loop:
   - Choose next idea from the running log using hypothesis -> evidence -> code mapping (not output-only intuition).
   - Inspect relevant source code before editing; confirm current bottleneck signals still match the chosen hypothesis.
   - Apply code/config changes.
   - Run `eval_command` once per step.
   - Run `profile_command` for changed hotspots (every step for kernel-level work, or at least every few steps when overhead is high).
   - Parse metric and update `best_value` and `delta_vs_best`.
   - Append a row for that step with hypothesis, evidence, and metadata.
   - Update idea log with what was tried, observed effect, and new candidates grounded in diagnostics + code context.
   - Continue forever.
5. Stop condition:
   - Only stop when the user explicitly interrupts/kills the run.
   - On interruption, keep the file intact and add a final note with the last completed step.

## Creative Optimization Rules

- Do not propose a new step without at least one concrete bottleneck signal from observability.
- Generate ideas across multiple levers, not just parameter twiddling:
  - Algorithm/dataflow changes (work reduction, fusion, better asymptotics).
  - Memory layout and movement (coalescing, caching, transfer overlap, prefetch).
  - Parallelism shape (tiling, vectorization, occupancy, launch config, thread mapping).
  - Scheduling/runtime knobs (streaming, batching, pipelining, compiler flags, precision).
- For CUDA workloads, require ideas to reference kernel-level evidence and owning code paths (kernel source, launch site, surrounding synchronization).
- When outputs improve but diagnostics regress (or vice versa), record the tradeoff explicitly and branch ideas accordingly.
- Periodically refresh profiling from scratch to avoid optimizing stale bottlenecks after earlier improvements.

## Reliability Rules

- Prefer long-running sessions (`tmux`/`screen`) for overnight/multi-day optimization.
- Do not change the metric protocol silently mid-run; if it must change, record a protocol change note in the file before continuing.
- Do not change the observability protocol silently mid-run; record changes before continuing.
- If a step fails (command error, parse failure, environment issue), write a row with `status=error`, include notes, and continue unless unrecoverable.
- Never skip recording attempted steps.
- Do not terminate just because progress stalls; continue proposing and testing ideas until stopped by the user.
