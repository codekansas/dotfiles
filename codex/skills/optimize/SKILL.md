---
name: "optimize"
description: "Use when the user provides natural-language instructions for what to optimize (for example ML loss, latency, or CUDA benchmark runtime) and wants a forever optimization loop. Infer the experiment setup from the codebase, write `optimization_results_<metric>.md` plus a machine-readable sidecar and progress graph, set up a Codex watcher when available, then iterate autonomously without stopping early until manually stopped."
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
5. Create a recovery plan before risky edits:
   - Use version control checkpoints when available (`git commit`, `git stash`, or an equivalent patch) so failed ideas can be reverted quickly.
   - Define a per-run timeout before the loop starts. If the evaluation has a known fixed budget, use that. Otherwise choose a conservative timeout and treat runs that exceed it as failures.

## Output Artifact Contract

- Always create these three files in the working directory before step 1 is recorded:
  - `optimization_results_<metric>.md`
  - `optimization_results_<metric>.tsv`
  - `optimization_progress_<metric>.svg`
- The Markdown file is the human-readable narrative.
- The TSV file is the authoritative machine-readable ledger used to render the graph.
- The graph must be regenerated after every recorded step, including baselines, regressions, and errors.
- Use the bundled renderer at `scripts/render_optimization_progress.py`.
- The graph must make it easy to answer two questions at a glance:
  - Which changes actually helped?
  - Is the target metric still moving in the desired direction?

## Watchdog Contract

- When running inside Codex and `CODEX_THREAD_ID` is available, set up the bundled watchdog before the baseline. This is mandatory when the runtime supports it.
- The watchdog must monitor the current Codex thread and, if that thread shuts down, send a follow-up prompt that tells the same thread to keep going.
- Resolve bundled scripts relative to this skill directory. Do not assume the target repository already contains these scripts.
- Use `.optimize_watchdog/` in the working directory for control files:
  - `watchdog.pid`
  - `watchdog.state.json`
  - `watchdog.log`
  - `STOP`
- Start the watcher idempotently. If a healthy watcher already exists for this working directory and thread, reuse it instead of starting a second copy.
- If the watcher cannot be enabled because `CODEX_THREAD_ID`, the `codex` CLI, AppleScript/Terminal support, or the local Codex state database is unavailable, record that fact in the results file and continue with the normal optimization loop instead of blocking.
- On macOS, the watcher may reopen the session in Terminal because `codex resume` needs an interactive TTY.
- If the human truly wants the loop to stay stopped, they must create `.optimize_watchdog/STOP` or terminate the watcher itself. Otherwise the watcher should revive the thread after shutdown.

Recommended startup flow:

```bash
mkdir -p .optimize_watchdog
optimize_watchdog_script="<absolute path to this skill>/scripts/watch_codex_optimize.py"
nohup python3 "$optimize_watchdog_script" \
  --thread-id "$CODEX_THREAD_ID" \
  --cwd "$PWD" \
  --state-dir "$PWD/.optimize_watchdog" \
  --resume-prompt "Keep going. Continue the existing optimization loop from the current results artifacts, progress graph, and idea log. Do not stop early. Choose the next evidence-backed experiment and continue." \
  > "$PWD/.optimize_watchdog/watchdog.log" 2>&1 &
```

Use this exact TSV header:

```tsv
step	timestamp_utc	metric_value	best_value	delta_vs_best	decision	hypothesis	evidence	metadata
```

Field rules:

- `decision` must be one of `baseline`, `keep`, `discard`, or `error`.
- `metric_value` must be numeric when parsing succeeds; leave it blank for hard failures.
- `best_value` is the best metric observed after that step.
- `delta_vs_best` should be `metric_value - best_value` for `minimize` objectives and `best_value - metric_value` for `maximize` objectives. This means `0` indicates a baseline or kept best, while positive values indicate worse-than-best runs.

Render the graph after each appended TSV row:

```bash
python scripts/render_optimization_progress.py \
  --input optimization_results_<metric>.tsv \
  --output optimization_progress_<metric>.svg \
  --metric-label "<metric>" \
  --direction <minimize|maximize>
```

Graph expectations:

- X-axis: experiment number (`step`)
- Y-axis: optimization metric, labeled with whether lower or higher is better
- Faint gray dots: discarded attempts
- Green markers: baseline and kept improvements
- Red `x` markers: error attempts when a metric value exists
- Green step line: running best after each experiment
- Short rotated labels for kept improvements so the winning ideas are immediately visible
- Title summarizing total experiment count and kept improvement count

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

## Progress Artifacts

- TSV ledger: `optimization_results_<metric>.tsv`
- Graph: `optimization_progress_<metric>.svg`
- Graph command: `python scripts/render_optimization_progress.py --input optimization_results_<metric>.tsv --output optimization_progress_<metric>.svg --metric-label "<metric>" --direction <minimize|maximize>`
- Watchdog state dir when available: `.optimize_watchdog/`

| step | timestamp_utc | metric_value | best_value | delta_vs_best | decision | hypothesis | evidence | metadata |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 | 2026-03-03T10:00:00Z | 0.1234 | 0.1234 | 0.0000 | baseline | establish control | profiler shows kernel_x dominates 62% runtime | sha=abc123; cfg=config.yaml |
| 2 | 2026-03-03T10:20:00Z | 0.1189 | 0.1189 | 0.0000 | keep | fuse post-processing kernels | trace shows launch overhead dominates tail kernels | sha=def456; cfg=config.yaml |
| 3 | 2026-03-03T10:40:00Z | 0.1210 | 0.1189 | 0.0021 | discard | increase tile width | occupancy improved but memory stalls increased | sha=ghi789; cfg=config.yaml |

## Idea Log (Running)

- [ ] Step 2 candidate: <idea>
  - Hypothesis: <why this should help>
  - Evidence link: <profiling/log lines + code location>
- [ ] Step 3 candidate: <idea>
  - Hypothesis: <why this should help>
  - Evidence link: <profiling/log lines + code location>
```

## Autonomous Optimization Workflow

1. Infer experiment setup from codebase context and initialize all three artifacts with the metric and observability protocols.
2. If the runtime exposes `CODEX_THREAD_ID`, start the watchdog before the baseline and record whether it was enabled successfully.
3. Establish observability first:
   - Add/enable toggleable diagnostics with minimal default overhead.
   - Capture a profiling/logging snapshot and map top bottlenecks to concrete code locations.
   - If instrumentation work was required, record that as the first logged step.
4. Run the baseline:
   - Execute `eval_command`.
   - Execute `profile_command` when gathering evidence for idea generation.
   - Parse metric via the protocol.
   - Record the baseline as the next step number in both the Markdown table and TSV ledger.
   - Render the graph immediately after writing the baseline row.
5. LOOP FOREVER:
   - Choose next idea from the running log using hypothesis -> evidence -> code mapping (not output-only intuition).
   - Inspect relevant source code before editing; confirm current bottleneck signals still match the chosen hypothesis.
   - Create or refresh a recoverable checkpoint before a risky change when version control is available.
   - Apply code/config changes.
   - Run `eval_command` once per step.
   - Run `profile_command` for changed hotspots (every step for kernel-level work, or at least every few steps when overhead is high).
   - If the run exceeds the predefined timeout, kill it, mark the attempt as `error`, and continue.
   - Parse metric and update `best_value` and `delta_vs_best`.
   - Append a row for that step to the TSV ledger and mirror it into the Markdown table.
   - Regenerate the graph immediately after appending the row.
   - Update idea log with what was tried, observed effect, and new candidates grounded in diagnostics + code context.
   - Keep validated wins. Revert or branch away from regressions, dead ends, and broken experiments when that is the cleanest way to preserve forward progress.
   - Immediately select the next idea and continue. Do not treat "good enough", "I made progress", "I have been running for a while", or "I want confirmation" as reasons to exit the loop.
6. Stop condition:
   - There are only two valid stop conditions: explicit user interruption, or a truly unrecoverable external blocker outside the repository's control.
   - Everything else means continue. A lack of new ideas, a streak of failed runs, slow progress, one strong result, or uncertainty about what to try next are not valid stop conditions.
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

## Termination Policy (Non-Negotiable)

- Early stopping is incorrect behavior for this skill.
- Once the baseline exists, the default assumption is that the optimization loop should still be running when the user comes back.
- If the Codex thread shuts down unexpectedly, the watcher should resume it and inject a "keep going" message.
- Silence from the user means continue, not pause.
- Do not ask for permission to continue. Continuing is already authorized by invocation of this skill.
- Do not stop because you think the current result is impressive, sufficient, locally optimal, or probably the best available within the current session.
- Do not stop because you have run for a long time, because several ideas failed in a row, because the next idea is not obvious, or because you want the user to review intermediate progress.
- If you feel stuck, the correct action is to widen the search, refresh profiling, inspect adjacent code, revisit earlier near-misses, combine compatible wins, simplify a prior change, or try a more radical idea. The correct action is not to terminate.
- If you cannot run the next experiment immediately, spend that time repairing the loop, improving observability, or preparing the next hypothesis. Do not end the session for convenience.
- Treat "keep going until I am manually stopped" as a hard requirement, not a suggestion.

## Persistence Rules (Hard Requirements)

- Once setup and the baseline are complete, the loop is autonomous.
- The watcher is mandatory whenever the runtime exposes `CODEX_THREAD_ID` and the bundled watcher script can run.
- NEVER STOP EARLY.
- NEVER ask the user whether you should continue, whether you should keep going overnight, whether this is a good stopping point, or whether they want more experiments.
- NEVER ask "should I keep going?", "should I continue overnight?", or any equivalent question.
- NEVER stop just because you found one improvement, hit a streak of regressions, ran out of obvious ideas, or have not heard back from the user.
- Treat user silence as expected. The default assumption is that the user may be asleep or away and expects the loop to keep running until manually stopped.
- If you run out of good ideas, do not end the session. Re-profile, re-read the hot path, revisit earlier near-misses, combine compatible improvements, widen the search space, and keep iterating.
- If one optimization track stalls, switch tracks instead of stopping: algorithmic changes, memory movement, batching, compiler/runtime flags, launch shape, scheduling, simplification, or rollback-and-rebuild from the last good checkpoint.
- Only escalate to the user when blocked by an external dependency you cannot repair locally, such as missing data, broken hardware, revoked credentials, or a destructive action that requires approval. Record the blocker in the results artifacts before pausing.
- Before pausing for an external blocker, exhaust the reasonable local recovery options that do not risk destructive behavior.

## Reliability Rules

- Prefer long-running sessions (`tmux`/`screen`) for overnight/multi-day optimization.
- Do not leave duplicate watchdogs running. Reuse the existing watcher or replace only a stale PID file.
- Do not change the metric protocol silently mid-run; if it must change, record a protocol change note in the file before continuing.
- Do not change the observability protocol silently mid-run; record changes before continuing.
- If a step fails (command error, parse failure, environment issue), write a row with `decision=error`, include notes, regenerate the graph, and continue unless unrecoverable.
- Never skip recording attempted steps.
- Do not terminate just because progress stalls; continue proposing and testing ideas until stopped by the user.
- If you must change tactics, keep the same artifact files and continue the step numbering so the graph remains a continuous history of the search.
- When in doubt between stopping and continuing, choose continuing.
