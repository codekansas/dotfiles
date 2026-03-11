#!/usr/bin/env python3
"""Render an optimization progress SVG from a TSV experiment ledger.

Args:
  --input: Path to the TSV ledger.
  --output: Path to the SVG output.
  --metric-label: Human-readable metric label for the Y axis.
  --direction: Whether the metric should be minimized or maximized.
  --max-label-length: Maximum length for kept-improvement labels.

Returns:
  Exit status 0 on success.
"""

import argparse
import csv
import html
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class ExperimentRow:
    step: int
    metric_value: "float | None"
    best_value: "float | None"
    decision: str
    hypothesis: str


def _parse_float(value: str) -> "float | None":
    text = value.strip()
    if not text:
        return None
    return float(text)


def _parse_rows(path: Path) -> list[ExperimentRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required_columns = {
            "step",
            "metric_value",
            "best_value",
            "decision",
            "hypothesis",
        }
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required TSV columns: {missing}")

        rows: list[ExperimentRow] = []
        for raw_row in reader:
            rows.append(
                ExperimentRow(
                    step=int(raw_row["step"]),
                    metric_value=_parse_float(raw_row["metric_value"]),
                    best_value=_parse_float(raw_row["best_value"]),
                    decision=raw_row["decision"].strip().lower(),
                    hypothesis=raw_row["hypothesis"].strip(),
                )
            )
    if not rows:
        raise ValueError("No experiment rows found in TSV ledger.")
    return rows


def _format_metric(value: float) -> str:
    return f"{value:.6f}"


def _short_label(text: str, max_length: int) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3].rstrip() + "..."


def _compute_y_ticks(y_min: float, y_max: float, count: int = 6) -> list[float]:
    if count < 2:
        return [y_min]
    step = (y_max - y_min) / (count - 1)
    return [y_min + idx * step for idx in range(count)]


def _compute_x_ticks(step_min: int, step_max: int, count: int = 8) -> list[int]:
    if step_min == step_max:
        return [step_min]
    if count < 2:
        return [step_min, step_max]
    span = step_max - step_min
    step_size = max(1, round(span / (count - 1)))
    ticks = list(range(step_min, step_max + 1, step_size))
    if ticks[-1] != step_max:
        ticks.append(step_max)
    return ticks


def _svg_escape(text: str) -> str:
    return html.escape(text, quote=True)


def _render_svg(
    rows: list[ExperimentRow],
    output_path: Path,
    metric_label: str,
    direction: str,
    max_label_length: int,
) -> None:
    valid_metric_rows = [row for row in rows if row.metric_value is not None]
    if not valid_metric_rows:
        raise ValueError("Cannot render graph without at least one numeric metric value.")

    step_values = [row.step for row in rows]
    step_min = min(step_values)
    step_max = max(step_values)
    metric_values = [row.metric_value for row in valid_metric_rows if row.metric_value is not None]
    best_values = [row.best_value for row in rows if row.best_value is not None]

    y_data_min = min(metric_values + best_values)
    y_data_max = max(metric_values + best_values)
    y_padding = max((y_data_max - y_data_min) * 0.08, abs(y_data_max) * 0.002, 1e-9)
    y_min = y_data_min - y_padding
    y_max = y_data_max + y_padding
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    width = 1600
    height = 900
    margin_left = 110
    margin_right = 60
    margin_top = 70
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    def x_pos(step: int) -> float:
        if step_max == step_min:
            return margin_left + plot_width / 2
        return margin_left + ((step - step_min) / (step_max - step_min)) * plot_width

    def y_pos(value: float) -> float:
        return margin_top + ((y_max - value) / (y_max - y_min)) * plot_height

    x_ticks = _compute_x_ticks(step_min, step_max)
    y_ticks = _compute_y_ticks(y_min, y_max)
    y_axis_label = f"{metric_label} ({'lower' if direction == 'minimize' else 'higher'} is better)"

    total_experiments = len(rows)
    kept_improvements = sum(1 for row in rows if row.decision == "keep")

    discard_rows = [row for row in rows if row.decision == "discard" and row.metric_value is not None]
    error_rows = [row for row in rows if row.decision == "error" and row.metric_value is not None]
    kept_rows = [
        row
        for row in rows
        if row.decision in {"baseline", "keep"} and row.metric_value is not None
    ]

    step_line_points: list[str] = []
    previous_x: "float | None" = None
    previous_y: "float | None" = None
    for row in rows:
        if row.best_value is None:
            continue
        current_x = x_pos(row.step)
        current_y = y_pos(row.best_value)
        if previous_x is None or previous_y is None:
            step_line_points.append(f"{current_x:.2f},{current_y:.2f}")
        else:
            step_line_points.append(f"{current_x:.2f},{previous_y:.2f}")
            step_line_points.append(f"{current_x:.2f},{current_y:.2f}")
        previous_x = current_x
        previous_y = current_y

    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{_svg_escape(metric_label)} progress chart">'
        ),
        '  <rect width="100%" height="100%" fill="#f3f4f6" />',
        (
            f'  <rect x="{margin_left}" y="{margin_top}" width="{plot_width}" '
            f'height="{plot_height}" fill="#fbfbfb" stroke="#d1d5db" />'
        ),
        (
            f'  <text x="{width / 2:.1f}" y="36" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="22" '
            f'fill="#111827">Optimization Progress: {total_experiments} '
            f'Experiments, {kept_improvements} Kept Improvements</text>'
        ),
        (
            f'  <text x="{width / 2:.1f}" y="{height - 18}" '
            'text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
            'font-size="18" fill="#111827">Experiment #</text>'
        ),
        f'  <g transform="translate(30 {height / 2:.1f}) rotate(-90)">',
        (
            '    <text text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="18" '
            f'fill="#111827">{_svg_escape(y_axis_label)}</text>'
        ),
        "  </g>",
    ]

    for tick in y_ticks:
        y = y_pos(tick)
        svg_lines.extend(
            [
                (
                    f'  <line x1="{margin_left}" y1="{y:.2f}" '
                    f'x2="{margin_left + plot_width}" y2="{y:.2f}" '
                    'stroke="#d1d5db" stroke-width="1" />'
                ),
                (
                    f'  <text x="{margin_left - 12}" y="{y + 5:.2f}" '
                    'text-anchor="end" font-family="Helvetica, Arial, sans-serif" '
                    f'font-size="14" fill="#374151">{_format_metric(tick)}</text>'
                ),
            ]
        )

    for tick in x_ticks:
        x = x_pos(tick)
        svg_lines.extend(
            [
                (
                    f'  <line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" '
                    f'y2="{margin_top + plot_height}" stroke="#e5e7eb" '
                    'stroke-width="1" />'
                ),
                (
                    f'  <text x="{x:.2f}" y="{margin_top + plot_height + 28}" '
                    'text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
                    f'font-size="14" fill="#374151">{tick}</text>'
                ),
            ]
        )

    if step_line_points:
        svg_lines.append(
            '  <polyline fill="none" stroke="#59c181" stroke-width="3.5" points="'
            + " ".join(step_line_points)
            + '" />'
        )

    for row in discard_rows:
        metric_value = cast(float, row.metric_value)
        svg_lines.append(
            (
                f'  <circle cx="{x_pos(row.step):.2f}" '
                f'cy="{y_pos(metric_value):.2f}" r="4" fill="#c9c9c9" '
                'fill-opacity="0.85" />'
            )
        )

    for row in error_rows:
        x = x_pos(row.step)
        metric_value = cast(float, row.metric_value)
        y = y_pos(metric_value)
        svg_lines.extend(
            [
                (
                    f'  <line x1="{x - 5:.2f}" y1="{y - 5:.2f}" '
                    f'x2="{x + 5:.2f}" y2="{y + 5:.2f}" '
                    'stroke="#dc2626" stroke-width="2" />'
                ),
                (
                    f'  <line x1="{x - 5:.2f}" y1="{y + 5:.2f}" '
                    f'x2="{x + 5:.2f}" y2="{y - 5:.2f}" '
                    'stroke="#dc2626" stroke-width="2" />'
                ),
            ]
        )

    for row in kept_rows:
        x = x_pos(row.step)
        metric_value = cast(float, row.metric_value)
        y = y_pos(metric_value)
        svg_lines.append(
            f'  <circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#2ecc71" stroke="#166534" stroke-width="1.5" />'
        )
        label = _short_label(
            row.hypothesis or ("baseline" if row.decision == "baseline" else row.decision),
            max_label_length,
        )
        if not label:
            continue
        if x > margin_left + plot_width * 0.82:
            text_anchor = "end"
            label_x = x - 8
        else:
            text_anchor = "start"
            label_x = x + 8
        label_y = y - 10
        svg_lines.append(
            f'  <text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="{text_anchor}" '
            'font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#2f855a" '
            f'transform="rotate(-32 {label_x:.2f} {label_y:.2f})">{_svg_escape(label)}</text>'
        )

    legend_x = width - 210
    legend_y = 85
    svg_lines.extend(
        [
            (
                f'  <rect x="{legend_x}" y="{legend_y - 18}" width="185" '
                'height="88" rx="8" fill="#ffffff" fill-opacity="0.92" '
                'stroke="#d1d5db" />'
            ),
            f'  <circle cx="{legend_x + 22}" cy="{legend_y}" r="4" fill="#c9c9c9" fill-opacity="0.85" />',
            (
                f'  <text x="{legend_x + 45}" y="{legend_y + 5}" '
                'font-family="Helvetica, Arial, sans-serif" font-size="14" '
                'fill="#111827">Discarded</text>'
            ),
            (
                f'  <circle cx="{legend_x + 22}" cy="{legend_y + 26}" '
                'r="6" fill="#2ecc71" stroke="#166534" stroke-width="1.5" />'
            ),
            (
                f'  <text x="{legend_x + 45}" y="{legend_y + 31}" '
                'font-family="Helvetica, Arial, sans-serif" font-size="14" '
                'fill="#111827">Kept</text>'
            ),
            (
                f'  <line x1="{legend_x + 10}" y1="{legend_y + 52}" '
                f'x2="{legend_x + 34}" y2="{legend_y + 52}" '
                'stroke="#59c181" stroke-width="3.5" />'
            ),
            (
                f'  <text x="{legend_x + 45}" y="{legend_y + 57}" '
                'font-family="Helvetica, Arial, sans-serif" font-size="14" '
                'fill="#111827">Running best</text>'
            ),
        ]
    )

    if error_rows:
        svg_lines.extend(
            [
                (
                    f'  <line x1="{legend_x + 17}" y1="{legend_y + 71}" '
                    f'x2="{legend_x + 27}" y2="{legend_y + 81}" '
                    'stroke="#dc2626" stroke-width="2" />'
                ),
                (
                    f'  <line x1="{legend_x + 17}" y1="{legend_y + 81}" '
                    f'x2="{legend_x + 27}" y2="{legend_y + 71}" '
                    'stroke="#dc2626" stroke-width="2" />'
                ),
                (
                    f'  <text x="{legend_x + 45}" y="{legend_y + 81}" '
                    'font-family="Helvetica, Arial, sans-serif" font-size="14" '
                    'fill="#111827">Error</text>'
                ),
            ]
        )

    svg_lines.append("</svg>")
    output_path.write_text("\n".join(svg_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the TSV ledger.")
    parser.add_argument("--output", required=True, help="Path to the SVG file to write.")
    parser.add_argument("--metric-label", required=True, help="Label for the graph's Y axis.")
    parser.add_argument(
        "--direction",
        required=True,
        choices=("minimize", "maximize"),
        help="Whether lower or higher metric values are better.",
    )
    parser.add_argument(
        "--max-label-length",
        type=int,
        default=48,
        help="Maximum label length for kept-improvement annotations.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = _parse_rows(input_path)
    _render_svg(rows, output_path, args.metric_label, args.direction, args.max_label_length)


if __name__ == "__main__":
    main()
