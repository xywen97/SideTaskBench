"""CLI for the graded similarity-level metrics."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .levels import LEVELS, build_report, load_level, pair_agreement
from .levels_render import write_level_report
from .metrics import json_ready


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Compute similarity-level metrics from graded coding runs")
    result.add_argument("--level", nargs=2, action="append", metavar=("LEVEL", "DIRECTORY"),
                        required=True,
                        help=f"One level's run directory; repeat to merge split directories. "
                             f"LEVEL is one of {', '.join(LEVELS)}")
    result.add_argument("--compare", nargs=2, action="append", metavar=("LEVEL", "DIRECTORY"),
                        default=[],
                        help="Same level re-run independently, for pair-level agreement only")
    result.add_argument("--output", type=Path, default=Path("metric_outputs_levels"))
    result.add_argument("--label", default=None, help="Run label recorded in the report")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    paths: dict[str, list[Path]] = defaultdict(list)
    for raw_level, directory in args.level:
        level = raw_level.upper()
        if level not in LEVELS:
            raise SystemExit(f"Unknown level: {raw_level}")
        paths[level].append(Path(directory))
    if not paths:
        raise SystemExit("At least one --level is required")

    by_level = {}
    for level, directories in paths.items():
        results = load_level(directories)
        conditions = {result["condition"] for result in results}
        if conditions != {"wrapped"}:
            raise SystemExit(f"{level} runs must all use wrapped: found {sorted(conditions)}")
        by_level[level] = results
        print(f"[levels] {level}: {len(results)} 次运行, {len({r['case_id'] for r in results})} 个配对")

    comparison_paths: dict[str, list[Path]] = defaultdict(list)
    for raw_level, directory in args.compare:
        level = raw_level.upper()
        if level not in LEVELS:
            raise SystemExit(f"Unknown level: {raw_level}")
        comparison_paths[level].append(Path(directory))
    comparison = {}
    for level, directories in comparison_paths.items():
        if level not in by_level:
            raise SystemExit(f"--compare {level} has no matching --level")
        comparison[level] = pair_agreement(by_level[level], load_level(directories))

    report = json_ready(build_report(by_level, comparison or None))
    if args.label:
        report["label"] = args.label
    write_level_report(args.output.resolve(), report)
    print(f"[levels] Wrote metrics to {args.output.resolve()}")
    return report


if __name__ == "__main__":
    main()
