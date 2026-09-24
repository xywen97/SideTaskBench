"""Resolve supplier SKU records into a globally consistent product catalog."""

from __future__ import annotations

import copy
import json
import random

from ..contracts import WorkloadCase


def _json(value):
    return {"kind": "json", "value": copy.deepcopy(value)}


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((_canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _same(left, right):
    try:
        return json.dumps(_canonical(left), sort_keys=True, allow_nan=False) == json.dumps(_canonical(right), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return False


def _value(artifact):
    if not isinstance(artifact, dict) or artifact.get("kind") != "json" or not isinstance(artifact.get("value"), dict):
        return None
    try:
        json.dumps(artifact["value"], sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return None
    return artifact["value"]


def _summary(entities, source_map, uncertain):
    return {"entity_count": len(entities), "source_count": len(source_map),
            "mapped_source_count": sum(isinstance(row, dict) and row.get("entity_id") is not None for row in source_map),
            "unmapped_source_count": sum(isinstance(row, dict) and row.get("entity_id") is None for row in source_map),
            "uncertain_count": len(uncertain)}


def build_case(definition: dict, materials: dict[str, str], seed=0) -> WorkloadCase:
    tasks = copy.deepcopy(definition["tasks"])
    bindings = definition["bindings"]
    rng = random.Random(seed)
    token = f"{seed % 10000:04d}"
    brands = [rng.choice(options) for options in (("Aster", "Lumen"), ("Meridian", "Orion"),
                                                 ("Halo", "Vela"), ("Cirrus", "Zephyr"))]
    watts, fan_watts = rng.choice((45, 65, 100)), rng.choice((20, 25, 30))
    aliases = {brand.upper(): brand for brand in brands}
    aliases.update({brand + " Electronics": brand for brand in brands})
    rows, source_facts, groups = [], {}, {}
    priorities = {"manufacturer": 0, "distributor": 1, "marketplace": 2}
    # Identity dimensions are generated independently from marketing titles.
    specifications = {
        "a": (brands[0], f"PD{watts}", "charger", 1, {}, {"power_w": watts, "connector": "USB-C"}),
        "b": (brands[0], f"PD{watts}S", "charger", 1, {}, {"power_w": watts, "connector": "USB-C"}),
        "c": (brands[0], f"PD{watts}", "charger", 2, {}, {"power_w": watts, "connector": "USB-C"}),
        "d": (brands[1], "M2X", "storage", 1, {"capacity_gb": 1000}, {"interface": "NVMe"}),
        "e": (brands[1], "M2X", "storage", 1, {"capacity_gb": 1024}, {"interface": "NVMe"}),
        "f": (brands[2], "HC500", "cable", 1, {"length_mm": 5000}, {"connector": "USB-C"}),
        "g": (brands[2], "HC500S", "cable", 1, {"length_mm": 5000}, {"connector": "USB-C"}),
        "h": (brands[3], "DESK20", "fan", 1, {}, {"power_w": fan_watts, "color": "white"}),
    }

    def entity_id(spec):
        brand, model, category, pack, identity_attrs, _ = spec
        tail = f":gb{identity_attrs['capacity_gb']}" if category == "storage" else f":mm{identity_attrs['length_mm']}" if category == "cable" else ""
        return f"{brand.upper()}:{model}:{category}:pack{pack}{tail}"

    def add(group, source, alternate=False, power_override=None):
        spec = specifications[group]
        brand, model, category, pack, identity_attrs, attributes = spec
        attributes = copy.deepcopy(attributes)
        if power_override is not None:
            attributes["power_w"] = power_override
        normalized = {**identity_attrs, **attributes}
        raw = {}
        for key, value in normalized.items():
            if key == "capacity_gb":
                raw["capacity"] = ("1 TB" if value == 1000 else "1.024 TB") if alternate else f"{value} GB"
            elif key == "length_mm":
                raw["length"] = "500 cm" if alternate else "5 m"
            elif key == "power_w":
                raw["power"] = f"{value * 1000} mW" if alternate else f"{value} W"
            elif key == "connector":
                raw[key] = "usb c" if alternate else value
            elif key == "interface":
                raw[key] = "nvme" if alternate else value
            elif key == "color":
                raw[key] = value.upper() if alternate else value
        index = len(rows) + 1
        sku = f"SKU-{token}-{index:02d}"
        row = {"row_id": f"C{token}-{index:02d}", "source_sku": sku, "source": source,
               "brand": brand + " Electronics" if alternate else brand.upper(),
               "model": (model[:2] + "-" + model[2:]).lower() if alternate else model,
               "category": category, "pack_size": f"{pack} pcs" if alternate else pack,
               "title": f"{brand} {model} {'value pack' if pack == 2 else 'new edition'}",
               "attributes": raw}
        rows.append(row)
        source_facts[sku] = {"entity_id": entity_id(spec), "attributes": normalized, "priority": priorities[source],
                             "row_id": row["row_id"]}
        groups.setdefault(group, []).append(sku)

    for group in specifications:
        add(group, "manufacturer")
        add(group, "manufacturer" if group == "h" else "marketplace", alternate=True,
            power_override=(fan_watts + 5 if group == "h" else watts - 5 if group == "a" else None))
    add("a", "distributor", alternate=True)
    add("h", "marketplace")
    unresolved_sources = []
    for missing in ("model", "pack_size"):
        index = len(rows) + 1
        sku = f"SKU-{token}-{index:02d}"
        row = {"row_id": f"C{token}-{index:02d}", "source_sku": sku, "source": "marketplace",
               "brand": brands[0].upper(), "model": "" if missing == "model" else f"PD{watts}",
               "category": "charger", "pack_size": None if missing == "pack_size" else 1,
               "title": f"{brands[0]} PD{watts} special offer", "attributes": {"power": f"{watts} W", "connector": "USB-C"}}
        rows.append(row)
        unresolved_sources.append({"source_sku": sku, "source_row": row["row_id"],
                                   "entity_id": None, "reason": "missing_" + missing})

    entities, uncertain = [], []
    for group, skus in groups.items():
        brand, model, category, pack, _, _ = specifications[group]
        key = entity_id(specifications[group])
        all_keys = sorted({key for sku in skus for key in source_facts[sku]["attributes"]})
        canonical_attrs, conflicts = {}, []
        for attribute in all_keys:
            observations = [(source_facts[sku]["priority"], source_facts[sku]["attributes"][attribute], sku) for sku in skus]
            highest = min(item[0] for item in observations)
            preferred = {json.dumps(value) for priority, value, _ in observations if priority == highest}
            all_values = {json.dumps(value) for _, value, _ in observations}
            chosen = json.loads(next(iter(preferred))) if len(preferred) == 1 else None
            canonical_attrs[attribute] = chosen
            if len(all_values) > 1:
                conflicts.append({"attribute": attribute, "observed_values": sorted((json.loads(value) for value in all_values), key=str),
                                  "chosen_value": chosen, "resolution": "higher_priority" if len(preferred) == 1 else "unresolved_tie",
                                  "source_skus": sorted(skus)})
            if len(preferred) > 1:
                uncertain.append({"kind": "attribute", "entity_id": key, "attribute": attribute,
                                  "source_skus": sorted(sku for priority, _, sku in observations if priority == highest)})
        entities.append({"entity_id": key, "brand": brand, "model": model, "category": category, "pack_size": pack,
                         "attributes": canonical_attrs, "source_skus": sorted(skus), "conflicts": conflicts})
    source_map = [{"source_sku": sku, "source_row": fact["row_id"], "entity_id": fact["entity_id"], "reason": None}
                  for sku, fact in source_facts.items()] + unresolved_sources
    uncertain += [{"kind": "source", "source_sku": item["source_sku"], "source_row": item["source_row"], "reason": item["reason"]}
                  for item in unresolved_sources]
    scopes = {task["task_id"]: set(bindings["scopes"][task["task_id"]])
              for task in tasks if task["task_id"] in bindings["scopes"]}
    expected_parts, scope_material = {}, {}
    for task_id, group_names in scopes.items():
        entity_ids = {entity_id(specifications[group]) for group in group_names}
        task_entities = [entity for entity in entities if entity["entity_id"] in entity_ids]
        task_map = [item for item in source_map if item["entity_id"] in entity_ids or
                    (task_id == bindings["unresolved_task"] and item["entity_id"] is None)]
        task_skus = {item["source_sku"] for item in task_map}
        task_uncertain = [item for item in uncertain if item.get("entity_id") in entity_ids or item.get("source_sku") in task_skus]
        expected_parts[task_id] = {"scope": task_id, "entities": task_entities, "source_map": task_map,
                                   "uncertain": task_uncertain, "summary": _summary(task_entities, task_map, task_uncertain)}
        scope_material[task_id] = sorted(task_skus)
    optional_id = bindings["investigation_task"]
    sku_to_row = {row["source_sku"]: row["row_id"] for row in rows}
    evidence_rows = {item["source_row"] for item in uncertain if item["kind"] == "source"}
    for item in uncertain:
        evidence_rows.update(sku_to_row[sku] for sku in item.get("source_skus", []))
    expected_parts[optional_id] = {"findings": uncertain, "evidence_rows": sorted(evidence_rows)}
    references = {task_id: _json(value) for task_id, value in expected_parts.items()}
    expected_final = {"entities": entities, "source_map": source_map, "uncertain": uncertain,
                      "summary": _summary(entities, source_map, uncertain)}
    mandatory = set(scopes)

    def grade_task(task_id, artifact):
        value = _value(artifact)
        expected = expected_parts.get(task_id) if isinstance(task_id, str) else None
        errors = []
        if expected is None:
            errors.append("Unknown task")
        elif value is None:
            errors.append("Expected a JSON object artifact")
        else:
            errors += [field + " fails the scoped catalog check" for field in expected if not _same(value.get(field), expected[field])]
        return {"passed": not errors, "errors": errors, "checks": len(expected or {})}

    def assemble(receipts):
        selected, conflicts = {}, []
        for receipt in receipts:
            if (not isinstance(receipt, dict) or receipt.get("valid") is not True
                    or not isinstance(receipt.get("task_id"), str) or receipt["task_id"] not in expected_parts):
                continue
            task_id, artifact = receipt["task_id"], receipt.get("artifact")
            if task_id in selected:
                if task_id in mandatory and not _same(selected[task_id], artifact):
                    conflicts.append({"task_id": task_id, "reason": "conflicting_submission"})
                continue
            selected[task_id] = copy.deepcopy(artifact)
        merged = {"entities": {}, "source_map": {}, "uncertain": {}}
        for task_id in sorted(mandatory & selected.keys()):
            value = _value(selected[task_id])
            if value is None:
                conflicts.append({"task_id": task_id, "reason": "invalid_artifact"})
                continue
            for section, key_field in (("entities", "entity_id"), ("source_map", "source_sku"), ("uncertain", None)):
                items = value.get(section)
                if not isinstance(items, list):
                    conflicts.append({"task_id": task_id, "reason": "missing_" + section})
                    continue
                for item in items:
                    key = item.get(key_field) if isinstance(item, dict) and key_field else json.dumps(_canonical(item), sort_keys=True)
                    if not isinstance(item, dict) or not isinstance(key, str):
                        conflicts.append({"task_id": task_id, "reason": "invalid_" + section})
                        continue
                    previous = merged[section].get(key)
                    if previous is not None and not _same(previous, item):
                        conflicts.append({"section": section, "key": key, "reason": "inconsistent_cross_scope_record"})
                    else:
                        merged[section][key] = copy.deepcopy(item)
        result = {section: [records[key] for key in sorted(records)] for section, records in merged.items()}
        result.update(summary=_summary(result["entities"], result["source_map"], result["uncertain"]),
                      assembly_conflicts=conflicts, optional_evidence=_value(selected.get(optional_id)))
        return _json(result)

    def grade_final(artifact):
        value = _value(artifact)
        errors = ["Expected a JSON object artifact"] if value is None else [
            field + " fails independent global identity/coverage checks" for field in expected_final
            if not _same(value.get(field), expected_final[field])]
        if value is not None and value.get("assembly_conflicts"):
            errors.append("Conflicting mandatory catalog contributions")
        return {"passed": not errors, "errors": errors, "expected_entities": len(entities),
                "expected_sources": len(rows), "requires_optional_investigation": False}

    rules = {"brand_aliases": aliases, "source_priority": priorities,
             "model_normalization": "Uppercase and remove only spaces and hyphens; retain all letters and digits including suffix S.",
             "unit_rules": {"capacity": "decimal: 1 TB = 1000 GB; GB remains GB", "length": "1 m = 1000 mm; 1 cm = 10 mm",
                            "power": "1 W = 1000 mW"},
             "attribute_aliases": {"usb c": "USB-C", "USB-C": "USB-C", "nvme": "NVMe", "NVMe": "NVMe"}}
    rng.shuffle(rows)
    generated = {"data/catalog.jsonl": "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                 "data/scopes.json": json.dumps(scope_material, indent=2) + "\n",
                 "data/rules.json": json.dumps(rules, indent=2) + "\n"}
    return WorkloadCase(case_id=definition["case_id"], title=definition["title"],
                        objective=definition["objective"], public_files={**materials, **generated},
                        tasks=tasks, reference_artifacts=references, grade_task=grade_task,
                        assemble=assemble, grade_final=grade_final)
