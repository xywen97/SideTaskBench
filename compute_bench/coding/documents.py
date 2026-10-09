"""Benchmark contexts for TaskForge's fixed reference treatments."""

import difflib
import json
from pathlib import Path

from taskforge.distribution import CONDITIONS, VARIANTS
from taskforge.distribution import render_reference as _render_reference


from compute_bench.workloads.host_tasks import compatibility_context


def reference_context(case: dict, *, strip_compatibility_context: bool = False) -> dict:
    ctx = compatibility_context(case.get("host_task_id", case["id"]))
    return {"topic": case["reference_topic"], "text": case["reference_text"],
            "compatibility_context": "" if strip_compatibility_context else ctx}


def render_reference(case: dict, condition: str, variant: str = "companion_v1",
                     *, strip_compatibility_context: bool = False) -> str:
    if condition not in CONDITIONS or variant not in VARIANTS:
        raise ValueError("Unknown reference treatment")
    return _render_reference(
        reference_context(case, strip_compatibility_context=strip_compatibility_context),
        case["crowd_task"], condition, variant)


def save_reference_comparisons(directory: Path, cases: list[dict], documents: dict,
                               plan: list[dict], variant: str) -> None:
    """Freeze pre-Agent reference comparisons outside the Agent's workspace."""
    entries, logs = [], []
    for case in cases:
        before = documents[case["id"]]["clean"]
        for condition, after in documents[case["id"]].items():
            trials = [trial for trial in plan
                      if trial["case_id"] == case["id"] and trial["condition"] == condition]
            if not trials:
                continue
            relative = Path("reference_comparisons") / case["id"] / condition
            target = directory / relative
            target.mkdir(parents=True, exist_ok=True)
            # Full context makes both the unchanged original and every addition visible.
            diff = "".join(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile="clean/docs/reference.md", tofile=f"{condition}/docs/reference.md",
                n=max(len(before.splitlines()), len(after.splitlines()))))
            for name, content in (("before.md", before), ("after.md", after), ("reference.diff", diff)):
                (target / name).write_text(content, encoding="utf-8")
            entry = {"case_id": case["id"], "task_id": case["crowd_task"]["task_id"],
                     "condition": condition, "variant": variant,
                     "run_ids": [trial["run_id"] for trial in trials],
                     "before": (relative / "before.md").as_posix(),
                     "after": (relative / "after.md").as_posix(),
                     "diff": (relative / "reference.diff").as_posix()}
            entries.append(entry)
            logs.append(
                f"=== reference.md 对比 | {case['id']} | t={entry['task_id']} | {condition} | {variant} ===\n"
                f"运行: {', '.join(entry['run_ids'])}\n"
                f"嵌入前（clean）: {entry['before']}\n处理后（Agent 初始正文）: {entry['after']}\n"
                "差异：- 为删除，+ 为新增，空格为原有正文。\n"
                + (diff if diff else "无变化。正文：\n" + before) + "\n")
    root = directory / "reference_comparisons"
    root.mkdir(exist_ok=True)
    (root / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log = "reference.md 在 Agent 启动前的材料对比；是否实际读取和完成子任务请查看轨迹与评分。\n\n" + "\n".join(logs)
    (directory / "reference_comparisons.log").write_text(log, encoding="utf-8")
