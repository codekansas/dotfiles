#!/usr/bin/env python3
"""Rewrite the optimization markdown summary from state and TSV artifacts.

Args:
  --state: Path to optimization_loop_state.json.
  --tsv: Path to the optimization TSV ledger.
  --output: Path to the markdown summary to write.

Returns:
  Exit status 0 on success.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import cast


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Path to optimization_loop_state.json.")
    parser.add_argument("--tsv", required=True, help="Path to the optimization TSV ledger.")
    parser.add_argument("--output", required=True, help="Path to the markdown summary output.")
    return parser.parse_args()


def _read_state(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _markdown_value(value: str) -> str:
    return value or "-"


def _build_lines(state: dict[str, object], rows: list[dict[str, str]]) -> list[str]:
    last_run = _as_dict(state.get("last_run"))
    pending = _as_dict(state.get("pending"))
    lines = [
        f"# Optimization Results: {_as_text(state.get('metric')) or 'metric'}",
        "",
        f"Direction: {_as_text(state.get('direction')) or 'minimize'}",
        f"Started: {_as_text(state.get('started_at_utc'))}",
        "",
        "## Metric Protocol",
        "",
        f"- Objective: {_as_text(state.get('objective'))}",
        f"- Eval command: `{_as_text(state.get('eval_command'))}`"
        if _as_text(state.get("eval_command"))
        else "- Eval command: ",
        (
            f"- Metric parser: `{_as_text(state.get('metric_pattern'))}` "
            f"(group {_as_text(state.get('metric_group')) or '1'})"
        )
        if _as_text(state.get("metric_pattern"))
        else "- Metric parser: ",
        f"- Value semantics: {_as_text(state.get('value_semantics'))}"
        if _as_text(state.get("value_semantics"))
        else "- Value semantics: ",
        f"- Fixed conditions: {_as_text(state.get('fixed_conditions'))}"
        if _as_text(state.get("fixed_conditions"))
        else "- Fixed conditions: ",
        "",
        "## Observability Protocol",
        "",
        f"- Profile command: `{_as_text(state.get('profile_command'))}`"
        if _as_text(state.get("profile_command"))
        else "- Profile command: ",
        f"- Run directory: `{_as_text(state.get('run_dir'))}`"
        if _as_text(state.get("run_dir"))
        else "- Run directory: ",
        f"- Graph: `{_as_text(state.get('results_graph'))}`"
        if _as_text(state.get("results_graph"))
        else "- Graph: ",
        "",
        "## Best Known Result",
        "",
        f"- Best value: {_as_text(state.get('best_value'))}"
        if _as_text(state.get("best_value"))
        else "- Best value: ",
        f"- Best reference: {_as_text(state.get('best_reference'))}"
        if _as_text(state.get("best_reference"))
        else "- Best reference: ",
        "",
        "## Last Run",
        "",
        f"- Step: {_as_text(last_run.get('step'))}" if _as_text(last_run.get("step")) else "- Step: ",
        f"- Outcome: {_as_text(last_run.get('outcome'))}"
        if _as_text(last_run.get("outcome"))
        else "- Outcome: ",
        f"- Metric value: {_as_text(last_run.get('metric_value'))}"
        if _as_text(last_run.get("metric_value"))
        else "- Metric value: ",
        f"- Log path: `{_as_text(last_run.get('log_path'))}`"
        if _as_text(last_run.get("log_path"))
        else "- Log path: ",
        f"- Hypothesis: {_as_text(last_run.get('hypothesis'))}"
        if _as_text(last_run.get("hypothesis"))
        else "- Hypothesis: ",
        f"- Evidence: {_as_text(last_run.get('evidence'))}"
        if _as_text(last_run.get("evidence"))
        else "- Evidence: ",
        f"- Metadata: {_as_text(last_run.get('metadata'))}"
        if _as_text(last_run.get("metadata"))
        else "- Metadata: ",
        f"- Last error: {_as_text(state.get('last_error'))}"
        if _as_text(state.get("last_error"))
        else "- Last error: ",
        "",
        (
            "| step | timestamp_utc | metric_value | best_value | delta_vs_best |"
            " decision | hypothesis | evidence | metadata |"
        ),
        "|---:|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.get("step", ""),
                    row.get("timestamp_utc", ""),
                    _markdown_value(row.get("metric_value", "")),
                    _markdown_value(row.get("best_value", "")),
                    _markdown_value(row.get("delta_vs_best", "")),
                    row.get("decision", "") or "-",
                    row.get("hypothesis", "") or "-",
                    row.get("evidence", "") or "-",
                    row.get("metadata", "") or "-",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Pending Experiment",
            "",
            f"- Hypothesis: {_as_text(pending.get('hypothesis'))}"
            if _as_text(pending.get("hypothesis"))
            else "- Hypothesis: ",
            f"- Evidence: {_as_text(pending.get('evidence'))}"
            if _as_text(pending.get("evidence"))
            else "- Evidence: ",
            f"- Metadata: {_as_text(pending.get('metadata'))}"
            if _as_text(pending.get("metadata"))
            else "- Metadata: ",
            f"- Experiment command: `{_as_text(pending.get('experiment_command'))}`"
            if _as_text(pending.get("experiment_command"))
            else "- Experiment command: ",
            f"- Timeout seconds: {_as_text(pending.get('timeout_seconds'))}"
            if _as_text(pending.get("timeout_seconds"))
            else "- Timeout seconds: ",
            "",
        ]
    )
    return lines


def main() -> None:
    args = _parse_args()
    state_path = Path(args.state).expanduser().resolve()
    tsv_path = Path(args.tsv).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    state = _read_state(state_path)
    rows = _read_rows(tsv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(_build_lines(state, rows)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
