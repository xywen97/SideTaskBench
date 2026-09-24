"""Normalize one source record; merge identities and provenance only at the platform."""

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
import json

from ..contracts import WorkloadCase
from .atomic_common import artifact, equal, select, value_of


def normalize(packet):
    data = packet["input"]
    row, rules = data["record"], data["rules"]
    base = {"source_sku": row["source_sku"], "source_row": row["row_id"], "source": row["source"],
            "priority": rules["source_priority"][row["source"]]}
    for field in ("model", "pack_size"):
        if row[field] in (None, ""):
            return {**base, "entity_id": None, "reason": "missing_" + field}
    brand = rules["brand_aliases"].get(row["brand"], row["brand"])
    model = row["model"].replace(" ", "").replace("-", "").upper()
    pack = int(str(row["pack_size"]).split()[0])
    attrs = {}
    for name, value in row["attributes"].items():
        if name in {"capacity", "length", "power"}:
            number, unit = value.split()
            factors = {"capacity": {"TB": 1000, "GB": 1}, "length": {"m": 1000, "cm": 10, "mm": 1},
                       "power": {"W": 1, "mW": Decimal("0.001")}}[name]
            normalized = Decimal(number) * factors[unit]
            if normalized != int(normalized):
                raise ValueError("These packets use integral normalized units")
            attrs[{"capacity": "capacity_gb", "length": "length_mm", "power": "power_w"}[name]] = int(normalized)
        elif name == "color":
            attrs[name] = value.lower()
        else:
            attrs[name] = rules["attribute_aliases"].get(value, value)
    category = row["category"]
    suffix = (f":gb{attrs['capacity_gb']}" if category == "storage" else
              f":mm{attrs['length_mm']}" if category == "cable" else "")
    return {**base, "entity_id": f"{brand.upper()}:{model}:{category}:pack{pack}{suffix}", "reason": None,
            "brand": brand, "model": model, "category": category, "pack_size": pack, "attributes": attrs}


def catalog(facts):
    groups, source_map, uncertain = defaultdict(list), [], []
    for fact in facts:
        source_map.append({k: fact[k] for k in ("source_sku", "source_row", "entity_id", "reason")})
        if fact["entity_id"] is None:
            uncertain.append({"kind": "source", **{k: fact[k] for k in ("source_sku", "source_row", "reason")}})
        else:
            groups[fact["entity_id"]].append(fact)
    entities = []
    for key, rows in sorted(groups.items()):
        entity = {k: rows[0][k] for k in ("entity_id", "brand", "model", "category", "pack_size")}
        skus = sorted(row["source_sku"] for row in rows)
        attrs, conflicts = {}, []
        for name in sorted({n for row in rows for n in row["attributes"]}):
            observations = [(r["priority"], r["attributes"][name], r["source_sku"]) for r in rows if name in r["attributes"]]
            priority = min(r[0] for r in observations)
            preferred = {json.dumps(v) for p, v, _ in observations if p == priority}
            values = {json.dumps(v) for _, v, _ in observations}
            chosen = json.loads(next(iter(preferred))) if len(preferred) == 1 else None
            attrs[name] = chosen
            if len(values) > 1:
                conflicts.append({"attribute": name, "observed_values": sorted(map(json.loads, values), key=str),
                                  "chosen_value": chosen, "resolution": "higher_priority" if len(preferred) == 1 else "unresolved_tie",
                                  "source_skus": skus})
            if len(preferred) > 1:
                uncertain.append({"kind": "attribute", "entity_id": key, "attribute": name,
                                  "source_skus": sorted(s for p, _, s in observations if p == priority)})
        entities.append({**entity, "attributes": attrs, "source_skus": skus, "conflicts": conflicts})
    source_map.sort(key=lambda r: r["source_sku"])
    uncertain.sort(key=lambda r: json.dumps(r, sort_keys=True))
    return {"entities": entities, "source_map": source_map, "uncertain": uncertain,
            "summary": {"entity_count": len(entities), "source_count": len(source_map),
                        "mapped_source_count": sum(r["entity_id"] is not None for r in source_map),
                        "unmapped_source_count": sum(r["entity_id"] is None for r in source_map), "uncertain_count": len(uncertain)}}


def build_case(definition, materials, seed=0):
    tasks = deepcopy(definition["tasks"])
    if any(t["packet"]["operation"] != "normalize_one_record" for t in tasks):
        raise ValueError("Unknown catalog packet")
    expected = {t["task_id"]: normalize(t["packet"]) for t in tasks}
    if len({v["source_sku"] for v in expected.values()}) != len(tasks):
        raise ValueError("Each packet owns exactly one distinct source record")
    final = catalog(expected.values())

    def grade_task(task_id, result):
        return {"passed": task_id in expected and equal(value_of(result), expected[task_id])}

    def assemble(receipts):
        selected, conflicts = select(receipts, expected)
        usable = {k: v for k, v in selected.items() if isinstance(v, dict) and set(v) == set(expected[k])}
        try:
            result = catalog(usable.values())
        except (KeyError, TypeError, ValueError):
            result = catalog([])
            conflicts.extend(selected)
        return artifact({**result, "assembly_conflicts": sorted(set(conflicts))})

    def grade_final(result):
        value = value_of(result)
        passed = (isinstance(value, dict) and not value.get("assembly_conflicts")
                  and all(equal(value.get(k), v) for k, v in final.items()))
        return {"passed": passed, "expected_sources": len(tasks), "expected_entities": len(final["entities"])}

    return WorkloadCase(definition["case_id"], definition["title"], definition["objective"], materials, tasks,
                        {k: artifact(v) for k, v in expected.items()}, grade_task, assemble, grade_final)
