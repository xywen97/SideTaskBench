"""CLI for computing publication metrics from completed experiments."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from .metrics import (
    call_analysis,
    json_ready,
    load_run_directories,
    main_metrics,
    pass_at_k_metrics,
    reference_metrics,
    select_repeat,
)
from .render import write_report


CONDITION_SOURCE = {
    "clean": "clean", "length_control": "length_control", "direct": "direct",
    "wrapped": "wrapped", "wrapped_boundary": "wrapped",
}
CONDITION_ORDER = {"clean": 0, "length_control": 1, "direct": 2, "wrapped": 3, "wrapped_boundary": 4}


def _progress(step: int, message: str) -> None:
    print(f"[{step}/5] {message}", file=sys.stderr, flush=True)


def _case_ids(results):
    return {result["case_id"] for result in results}


def _require_same_cases(model, label, results, clean_results):
    actual, expected = _case_ids(results), _case_ids(clean_results)
    if actual != expected:
        raise SystemExit(
            f"{model}/{label} case coverage differs from clean: "
            f"missing={len(expected - actual)}, extra={len(actual - expected)}"
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Compute benchmark tables from immutable coding runs")
    result.add_argument("--main-run", nargs=3, action="append", metavar=("MODEL", "CONDITION", "DIRECTORY"), required=True,
                        help="Main-table run; repeat to merge split directories")
    result.add_argument("--analysis-run", nargs=2, action="append", metavar=("MODEL", "DIRECTORY"), default=[],
                        help="Full wrapped run used for reference-count and call analysis")
    result.add_argument("--pass-run", nargs=3, action="append", metavar=("MODEL", "BUDGET", "DIRECTORY"), default=[],
                        help="Independent k-repeat wrapped run; repeat to merge split directories")
    result.add_argument("--main-repeat", type=int, default=1, help="Repeat selected for the single-run main table")
    result.add_argument("--block-marker", default="Work unit:", help="Marker required with atomic task id for Block Seen")
    result.add_argument("--output", type=Path, default=Path("metric_outputs"))
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.main_repeat < 1:
        raise SystemExit("--main-repeat must be positive")
    main_paths: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for model, condition, directory in args.main_run:
        if condition not in CONDITION_SOURCE:
            raise SystemExit(f"Unknown condition: {condition}")
        main_paths[(model, condition)].append(Path(directory))
    _progress(1, "Loading and validating main-table runs")
    main_loaded = {key: load_run_directories(paths) for key, paths in main_paths.items()}
    models = sorted({model for model, _ in main_paths})
    clean_by_model = {}
    for model in models:
        key = (model, "clean")
        if key not in main_loaded:
            raise SystemExit(f"A clean --main-run is required for {model}")
        clean_by_model[model] = select_repeat(main_loaded[key][0], args.main_repeat)
    _progress(2, "Computing condition and token-overhead metrics")
    main_rows = []
    for (model, condition), (results, _) in sorted(
        main_loaded.items(), key=lambda item: (item[0][0], CONDITION_ORDER[item[0][1]])
    ):
        selected = select_repeat(results, args.main_repeat)
        _require_same_cases(model, condition, selected, clean_by_model[model])
        if len(selected) != len(_case_ids(selected)):
            raise SystemExit(f"{model}/{condition} has duplicate cases at repeat {args.main_repeat}")
        main_rows.append(main_metrics(
            model, condition, selected, clean_by_model[model], marker=args.block_marker,
            result_condition=CONDITION_SOURCE[condition],
        ))

    analysis_paths: dict[str, list[Path]] = defaultdict(list)
    for model, directory in args.analysis_run:
        analysis_paths[model].append(Path(directory))
    reference_rows = []
    calls = {"hosts": [], "correlations": [], "outcomes": []}
    _progress(3, "Computing reference-count and LLM-call analyses")
    for model, paths in sorted(analysis_paths.items()):
        if model not in clean_by_model:
            raise SystemExit(f"Analysis model lacks a clean main run: {model}")
        results, reference_counts = load_run_directories(paths)
        if any(result["condition"] != "wrapped" for result in results):
            raise SystemExit(f"Analysis runs must use wrapped condition: {model}")
        _require_same_cases(model, "analysis", results, clean_by_model[model])
        repeats_per_case = {case: 0 for case in _case_ids(results)}
        for result in results:
            repeats_per_case[result["case_id"]] += 1
        if len(set(repeats_per_case.values())) != 1:
            raise SystemExit(f"Analysis run has uneven repeat coverage: {model}")
        reference_rows.extend(reference_metrics(model, results, reference_counts, marker=args.block_marker))
        item = call_analysis(model, results, clean_by_model[model], reference_counts)
        for key in calls:
            calls[key].extend(item[key])

    pass_paths: dict[tuple[str, int], list[Path]] = defaultdict(list)
    for model, raw_budget, directory in args.pass_run:
        try:
            budget = int(raw_budget)
        except ValueError as exc:
            raise SystemExit(f"Invalid pass budget: {raw_budget}") from exc
        if budget < 1:
            raise SystemExit("Pass budgets must be positive")
        pass_paths[(model, budget)].append(Path(directory))
    pass_rows = []
    _progress(4, "Computing pass@k metrics")
    for (model, budget), paths in sorted(pass_paths.items(), key=lambda item: (item[0][0], item[0][1])):
        results, _ = load_run_directories(paths)
        if any(result["condition"] != "wrapped" for result in results):
            raise SystemExit(f"Pass@k runs must use wrapped condition: {model}/{budget}")
        pass_rows.append(pass_at_k_metrics(model, budget, results))

    report = json_ready({
        "schema_version": 1,
        "definitions": {
            "main_repeat": args.main_repeat,
            "block_seen": f"atomic_task_id and {args.block_marker!r} occur in model-visible tool output",
            "attempt": "submission_attempted=true",
            "valid_delivery": "valid_delivery=true",
            "token_delta": "paired mean among attempted condition runs versus matching clean case",
        },
        "main_table": main_rows,
        "reference_analysis": reference_rows,
        "pass_at_k": pass_rows,
        "call_analysis": calls,
    })
    _progress(5, "Writing JSON, Markdown, and CSV artifacts")
    write_report(args.output.resolve(), report)
    print(f"Wrote metrics to {args.output.resolve()}")
    return report
