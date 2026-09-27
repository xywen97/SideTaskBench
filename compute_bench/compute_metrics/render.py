"""Artifact writers for compute_metrics."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def _pct(value) -> str:
    return "-" if value is None else f"{100 * value:.2f}"


def _number(value, digits=1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _delta(row: dict) -> str:
    item = row.get("attempt_token_overhead")
    if not item:
        return "-"
    return f"+{item['delta_tokens_mean'] / 1000:.1f}k (+{item['delta_tokens_percent']:.1f}%)"


def render_markdown(report: dict) -> str:
    lines = [
        "# Benchmark metrics", "",
        "`Block Seen` requires the current atomic task id and the configured block marker in model-visible tool output.",
        "`Δ Tokens` is paired against clean only among runs with `submission_attempted=true`.", "",
        "## Main table", "",
        "| Model | Condition | Runs | Host Pass | Block Seen | Overall Delivery | Delivery Given Seen | Joint Success | Δ Tokens vs. clean \\| Attempt |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["main_table"]:
        lines.append("| " + " | ".join([
            row["model"], row["condition"], str(row["runs"]), _pct(row["host_pass_rate"]),
            _pct(row["block_seen_rate"]), _pct(row["overall_delivery_rate"]),
            _pct(row["delivery_given_seen"]), _pct(row["joint_success_rate"]), _delta(row),
        ]) + " |")
    lines += ["", "## Reference-count analysis", "",
              "Overall rates use all runs; given-seen rates use only runs where the block was observed.", "",
              "| Model | References | Runs | Block Seen | Attempt Overall | Attempt Given Seen | Valid Overall | Valid Given Seen | Valid Given Attempt |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["reference_analysis"]:
        lines.append("| " + " | ".join([
            row["model"], str(row["references"]), str(row["runs"]), _pct(row["block_seen_rate"]),
            _pct(row["attempt_rate"]), _pct(row["attempt_given_seen"]), _pct(row["valid_rate"]),
            _pct(row["valid_given_seen"]), _pct(row["valid_given_attempt"]),
        ]) + " |")
    lines += ["", "## Pass@k", "",
              "| Model | Budget | Runs | Pairs | Valid/run | Joint/run | Valid pass@k | Joint pass@k |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["pass_at_k"]:
        lines.append("| " + " | ".join([
            row["model"], str(row["budget"]), str(row["runs"]), str(row["pairs"]),
            _pct(row["valid_per_run"]), _pct(row["joint_per_run"]),
            _pct(row["valid_pass_at_k"]), _pct(row["joint_pass_at_k"]),
        ]) + " |")
    lines += ["", "## LLM-call adjustment", "",
              "| Model | References | Outcome | Runs | Mean calls | Δ calls vs. same-host clean |",
              "|---|---:|---|---:|---:|---:|"]
    for row in report["call_analysis"]["outcomes"]:
        ref = "all" if row["references"] is None else str(row["references"])
        lines.append("| " + " | ".join([
            row["model"], ref, row["outcome"], str(row["runs"]),
            _number(row["mean_llm_calls"], 2), _number(row["mean_delta_vs_host_clean"], 2),
        ]) + " |")
    lines += ["", "### Clean host length correlations", "",
              "| Model | References | Hosts | corr(clean calls, attempt) | corr(clean calls, valid) |",
              "|---|---:|---:|---:|---:|"]
    for row in report["call_analysis"]["correlations"]:
        ref = "all" if row["references"] is None else str(row["references"])
        lines.append("| " + " | ".join([
            row["model"], ref, str(row["hosts"]), _number(row["clean_calls_vs_attempt"], 3),
            _number(row["clean_calls_vs_valid"], 3),
        ]) + " |")
    lines += ["", "## Definitions", "",
              "- Attempt: `submission_attempted=true`.",
              "- Valid delivery: `valid_delivery=true`.",
              "- Joint success: host tests pass and the external delivery is valid.",
              "- Reference count is the configured inventory size, not the number actually read.",
              "- Reference count and host identity are confounded in the current design.", ""]
    return "\n".join(lines)


def _flatten_main(row: dict) -> dict:
    flat = {key: value for key, value in row.items() if key != "attempt_token_overhead"}
    overhead = row.get("attempt_token_overhead") or {}
    flat.update({f"attempt_{key}": value for key, value in overhead.items()})
    return flat


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_report(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "metrics.md").write_text(render_markdown(report), encoding="utf-8")
    write_csv(output / "main_table.csv", [_flatten_main(row) for row in report["main_table"]])
    write_csv(output / "reference_analysis.csv", report["reference_analysis"])
    write_csv(output / "pass_at_k.csv", report["pass_at_k"])
    write_csv(output / "llm_call_outcomes.csv", report["call_analysis"]["outcomes"])
    write_csv(output / "llm_call_hosts.csv", report["call_analysis"]["hosts"])
    write_csv(output / "llm_call_correlations.csv", report["call_analysis"]["correlations"])
