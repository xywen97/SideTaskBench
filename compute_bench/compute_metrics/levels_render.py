"""Artifact writers for the graded similarity-level metrics."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .levels import CATEGORY_ORDER, LEVELS


def _pct(value) -> str:
    return "-" if value is None else f"{value:.1f}"


def _z(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def _number(value, digits=1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render_markdown(report: dict) -> str:
    lines = [
        "# 相似度分级指标", "",
        "`Valid given seen` 是主指标：只在参考正文确实被返回给模型的运行里，计算有效交付比例。",
        "级别内交付率会被 category 构成影响，因此下面同时给出分级 × 类别矩阵和标准化结果。", "",
        "## 分级总表", "",
        "| 级别 | 名称 | 运行数 | 配对数 | Host Pass | Exposed | Attempt | Valid | Valid given seen | Joint |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["levels"]:
        name = report["definitions"]["levels"].get(row["level"], "")
        lines.append("| " + " | ".join([
            row["level"], name, str(row["runs"]), str(row["pairs"]),
            _pct(row["host_pass_rate"]), _pct(row["exposed_rate"]), _pct(row["attempt_rate"]),
            _pct(row["valid_rate"]), _pct(row["valid_given_seen"]), _pct(row["joint_success_rate"]),
        ]) + " |")

    matrix = report["category_matrix"]
    lines += ["", "## 分级 × 类别矩阵（Valid given seen）", "",
              "单元格是 `valid given seen / 运行数`。空单元格表示该级别没有这个类别的单元。", "",
              "| 级别 | " + " | ".join(matrix["categories"]) + " |",
              "|---|" + "---:|" * len(matrix["categories"])]
    index = {(row["level"], row["category"]): row for row in matrix["grid"]}
    for level in LEVELS:
        cells = []
        for category in matrix["categories"]:
            row = index.get((level, category))
            cells.append("-" if row is None
                         else f"{_pct(row['valid_given_seen'])} (n={row['runs']})")
        lines.append("| " + " | ".join([level, *cells]) + " |")

    lines += ["", "### 同类内的端到端差距（L3 − L0）", "",
              "只在同一个类别内部比较，去掉类别构成带来的差异。", "",
              "| 类别 | L3 | L0 | 差距 | L3 运行数 | L0 运行数 |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in matrix["endpoint_gaps"]:
        lines.append("| " + " | ".join([
            row["category"], _pct(row["l3"]), _pct(row["l0"]),
            _number(row["delta_points"]), str(row["l3_runs"]), str(row["l0_runs"]),
        ]) + " |")

    standardized = report["standardized"]
    lines += ["", "## 按类别构成标准化", "",
              "把每个级别按各级合计的类别权重重新加权，看梯度有多少来自类别构成。", "",
              "`覆盖权重` 是该级别拥有的类别的池化权重之和，未覆盖的类别不计入该行；",
              "覆盖权重低于 100% 说明这个级别缺少某些类别，其标准化结果只代表已覆盖部分。", "",
              "| 级别 | 原始 | 标准化 | 覆盖权重 |",
              "|---|---:|---:|---:|"]
    for row in standardized["rows"]:
        lines.append("| " + " | ".join([
            row["level"], _pct(row["raw_valid_given_seen"]),
            _pct(row["standardized_valid_given_seen"]), _pct(row["mix_coverage"]),
        ]) + " |")

    lines += ["", "## 相邻级别与端点差异", "",
              "两比例合并 z 检验，基于 valid given seen 的 exposed 样本量。", "",
              "| 对比 | 前一级 | 后一级 | 差 (pp) | z | 样本量 |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in report["adjacency"]:
        lines.append("| " + " | ".join([
            row["contrast"], _pct(row["first_rate"]), _pct(row["second_rate"]),
            _number(row["delta_points"]), _z(row["z"]),
            f"{row['first_trials']}/{row['second_trials']}",
        ]) + " |")

    contrasts = report["unit_contrasts"]
    lines += ["", "## 同一单元跨级别对照", "",
              "同一个原子任务在不同主任务下被判到不同级别。单元本身固定，只有标签变化，",
              "因此这是对「相似度而非任务难度在起作用」最直接的检验。仅列出每个级别至少 8 次运行的单元。", "",
              "| 原子任务 | 各级交付率 | 趋势 |",
              "|---|---|---|"]
    for row in contrasts:
        cells = [f"{level}={_pct(rate)} (n={n})"
                 for level, rate, n in zip(row["levels"], row["rates"], row["n"])]
        trend = {"decreasing": "随级别降低而下降", "increasing": "反向", "mixed": "非单调"}[row["trend"]]
        lines.append("| " + " | ".join([row["atomic_task_id"], "、".join(cells), trend]) + " |")
    if not contrasts:
        lines.append("| （无满足条件的单元） | | |")

    if "comparison" in report:
        lines += ["", "## 同配置重跑的配对一致率", "",
                  "配对级结论在低重复次数下不稳定，因此只报告一致率而不使用单配对结果。", "",
                  "| 级别 | 共同配对数 | 计数完全一致 | 一致率 | 零/非零判定一致 | 一致率 |",
                  "|---|---:|---:|---:|---:|---:|"]
        for level, row in sorted(report["comparison"].items()):
            lines.append("| " + " | ".join([
                level, str(row["pairs"]), str(row["identical_counts"]), _pct(row["identical_rate"]),
                str(row["same_zero_status"]), _pct(row["same_zero_status_rate"]),
            ]) + " |")

    lines += ["", "## 定义", "",
              "- Exposed：工具输出中实际返回了处理过的主参考正文。",
              "- Valid given seen：`valid_delivery` / `exposed`，本报告的主指标。",
              "- 标准化：按各级合计的 category 权重做直接标准化。",
              "- 同一单元跨级别对照：一个原子任务被多个主任务以不同级别使用时构成天然对照。", ""]
    return "\n".join(lines)


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


def write_level_report(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "levels_metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "levels_metrics.md").write_text(render_markdown(report), encoding="utf-8")
    write_csv(output / "levels_table.csv", report["levels"])
    write_csv(output / "levels_category_matrix.csv", report["category_matrix"]["grid"])
    write_csv(output / "levels_endpoint_gaps.csv", report["category_matrix"]["endpoint_gaps"])
    write_csv(output / "levels_standardized.csv", report["standardized"]["rows"])
    write_csv(output / "levels_adjacency.csv", report["adjacency"])
    write_csv(output / "levels_unit_contrasts.csv", report["unit_contrasts"])
    write_csv(output / "levels_pairs.csv", report["pairs"])
    if "comparison" in report:
        write_csv(output / "levels_comparison.csv",
                  [{"level": level, **row} for level, row in report["comparison"].items()])
