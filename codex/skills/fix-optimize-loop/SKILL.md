---
name: "fix-optimize-loop"
description: "Use when the optimize loop hits a bug in experiment execution, metric parsing, state bookkeeping, artifact generation, or checkpoint recovery. Diagnose the problem, patch the loop or repo as needed, make .optimize/<DATETIME>/optimization_loop_state.json consistent again, and exit so the parent optimize coordinator can continue."
---

## Purpose

- This is the bounded repair worker for the long-running `optimize` skill.
- It is invoked in a subagent only when some part of the loop is broken.
- The parent optimize coordinator may reuse the same subagent thread for many separate repair requests.
- It should repair the loop and return control to the parent coordinator.
- It does not own the optimization loop and must never take over future iterations.

## Required Inputs

The parent optimize coordinator should provide:

- the target working directory
- the absolute path to `.optimize/<DATETIME>/optimization_loop_state.json`
- the current `last_error`
- the relevant run log path when one exists
- any failing command output that explains the bug
- the current `.optimize/<DATETIME>/` run directory

## Repair Targets

This skill may repair:

- the experiment code
- the experiment command or timeout in `pending`
- the metric parser
- the results TSV or Markdown generation flow
- the SVG graph generation flow
- the loop support scripts
  - `../do-optimize-step/scripts/render_optimization_progress.py`
  - `../do-optimize-step/scripts/update_optimization_markdown.py`
- the repository recovery strategy for keep/discard handling
- inconsistent or incomplete state in `.optimize/<DATETIME>/optimization_loop_state.json`

## Workflow

1. Read `.optimize/<DATETIME>/optimization_loop_state.json`.
2. Read the failing log files, results artifacts, and relevant repository code.
3. Identify the smallest high-leverage fix that gets the optimization loop moving again.
4. Patch the code, config, state, or helper script as needed.
5. Make the state file coherent before exiting.

## State Repair Rules

Before exiting:

- Clear `last_error` if the loop is ready to resume.
- If the same experiment should be retried, leave a valid `pending` block.
- If a new experiment should be planned instead, clear `pending.experiment_command` so the parent coordinator knows to call `$do-optimize-step`.
- If `last_run` contains useful information that was not yet logged, preserve it instead of deleting it.

## Boundaries

- Do not stop the overall optimization loop.
- Do not take ownership of the overall optimization loop.
- Do not ask the human for confirmation unless an external blocker truly requires it.
- Do not turn into a general optimization worker; repair the loop, make the state consistent, and exit.
