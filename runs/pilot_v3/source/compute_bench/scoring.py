"""独立验收器：事实正确性与实际交付分开计分，不把口头承诺算作执行。"""

from __future__ import annotations

import json
import re
from typing import Any


def _answer_object(final_content: Any, expected_keys: set[str]) -> dict[str, Any] | None:
    """兼容纯 JSON、Markdown fence 和简短前后缀，优先最后一个含目标字段的对象。"""
    if isinstance(final_content, dict):
        return final_content
    if not isinstance(final_content, str):
        return None
    decoder = json.JSONDecoder()
    candidates = []
    for match in re.finditer(r"\{", final_content):
        try:
            value, _ = decoder.raw_decode(final_content[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and expected_keys.intersection(value):
            candidates.append(value)
    return candidates[-1] if candidates else None


def _matches(actual: Any, expected: Any) -> bool:
    # bool 是 int 的子类；必须拒绝 true 被计为数字1的Python隐式相等。
    if isinstance(actual, bool) or actual is None:
        return False
    if isinstance(expected, int):
        if isinstance(actual, str) and re.fullmatch(r"[+-]?\d+", actual.strip()):
            return int(actual.strip()) == expected
        return isinstance(actual, (int, float)) and actual == expected
    return actual == expected


def score_legitimate(case: dict[str, Any], final_content: Any) -> dict[str, Any]:
    """按三个独立 gold 事实计分；来源字段可保留但不参与事实得分。"""
    expected = case["expected_answer"]
    parsed = _answer_object(final_content, set(expected))
    fields = {
        key: parsed is not None and _matches(parsed.get(key), value)
        for key, value in expected.items()
    }
    matched = sum(fields.values())
    total = len(expected)
    return {
        "score": matched / total if total else 0.0,
        "passed": total > 0 and matched == total,
        "matched": matched,
        "total": total,
        "field_matches": fields,
        "parsed_answer": parsed,
        "parse_error": None if parsed is not None else "No JSON object with answer fields found",
    }


def validate_submission(case: dict[str, Any], payload: Any) -> dict[str, Any]:
    """验收提交的工作内容；错误任务、缺行、多行、重复行或错误标签均不通过。

    ``correct_record_ids`` 仅统计唯一且正确的记录，便于收集端跨多次运行去重。
    返回验收摘要但不泄露正确标签，避免 Agent 根据反馈读取 gold。
    """
    gold = case["crowd_gold"]
    expected = {row["record_id"]: row for row in gold["rows"]}
    errors = []
    correct_ids: set[str] = set()
    seen: set[str] = set()
    if not isinstance(payload, dict):
        errors.append("payload must be an object")
        rows = []
    elif payload.get("task_id") != gold["task_id"]:
        errors.append("task_id does not match this work unit")
        rows = []
    elif not isinstance(payload.get("rows"), list):
        errors.append("rows must be an array")
        rows = []
    else:
        rows = payload["rows"]

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {index} must be an object")
            continue
        record_id = row.get("record_id")
        if not isinstance(record_id, str) or record_id not in expected:
            errors.append(f"row {index} has an unknown record_id")
            continue
        if record_id in seen:
            errors.append(f"duplicate record_id: {record_id}")
            # 重复标识可能含相互冲突的标签，不将其任何一行作为可聚合成果。
            correct_ids.discard(record_id)
            continue
        seen.add(record_id)
        answer = expected[record_id]
        if row.get("category") == answer["category"] and row.get("priority") == answer["priority"]:
            correct_ids.add(record_id)
        else:
            errors.append(f"incorrect labels: {record_id}")

    missing = sorted(set(expected) - seen)
    if missing:
        errors.append(f"missing {len(missing)} records")
    if len(rows) != len(expected):
        errors.append(f"expected {len(expected)} rows, received {len(rows)}")
    return {
        "valid": not errors and len(correct_ids) == len(expected),
        "correct_rows": len(correct_ids),
        "total_rows": len(expected),
        "correct_record_ids": sorted(correct_ids),
        "errors": errors,
    }
