#!/usr/bin/env python3
"""Reference implementation for the supplier catalog normalization.

Builds the canonical catalog from materials/data/catalog.jsonl + rules.json and
then produces the optional investigation report (findings + evidence_rows).
"""
import json
import re
from collections import defaultdict

BASE = "/workspace/materials/data"

rules = json.load(open(f"{BASE}/rules.json"))
brand_aliases = rules["brand_aliases"]
priority = rules["source_priority"]
attr_aliases = rules["attribute_aliases"]

rows = [json.loads(l) for l in open(f"{BASE}/catalog.jsonl") if l.strip()]


def norm_model(m):
    if m is None:
        return None
    s = m.strip()
    if s == "":
        return None
    return re.sub(r"[ \-]", "", s).upper()


def norm_brand(b):
    return brand_aliases.get(b, b)


def parse_pack(p):
    if p is None:
        return None
    if isinstance(p, int):
        return p
    s = str(p).strip().lower()
    m = re.fullmatch(r"(\d+)\s*pcs", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"(\d+)", s)
    if m:
        return int(m.group(1))
    return None


def norm_power(v):
    s = str(v).strip()
    m = re.fullmatch(r"([\d.]+)\s*mW", s)
    if m:
        return int(round(float(m.group(1))))
    m = re.fullmatch(r"([\d.]+)\s*W", s)
    if m:
        return int(round(float(m.group(1)) * 1000))
    raise ValueError(v)


def norm_capacity(v):
    s = str(v).strip()
    m = re.fullmatch(r"([\d.]+)\s*TB", s)
    if m:
        return int(round(float(m.group(1)) * 1000))
    m = re.fullmatch(r"([\d.]+)\s*GB", s)
    if m:
        return int(round(float(m.group(1))))
    raise ValueError(v)


def norm_length(v):
    s = str(v).strip()
    m = re.fullmatch(r"([\d.]+)\s*mm", s)
    if m:
        return int(round(float(m.group(1))))
    m = re.fullmatch(r"([\d.]+)\s*cm", s)
    if m:
        return int(round(float(m.group(1)) * 10))
    m = re.fullmatch(r"([\d.]+)\s*m", s)
    if m:
        return int(round(float(m.group(1)) * 1000))
    raise ValueError(v)


def norm_alias(v):
    return attr_aliases.get(str(v), str(v))


def norm_color(v):
    return str(v).lower()


CANON = {
    "power": ("power_w", norm_power),
    "capacity": ("capacity_gb", norm_capacity),
    "length": ("length_mm", norm_length),
    "connector": ("connector", norm_alias),
    "interface": ("interface", norm_alias),
    "color": ("color", norm_color),
}


def normalize_row(r):
    """Return a dict with normalized identity + attributes, or an unresolved marker."""
    model = norm_model(r.get("model"))
    pack = parse_pack(r.get("pack_size"))
    if model is None:
        return {"unresolved": "missing_model"}
    if pack is None:
        return {"unresolved": "missing_pack_size"}
    brand = norm_brand(r["brand"])
    category = r["category"]
    attrs = {}
    for k, v in (r.get("attributes") or {}).items():
        ck, fn = CANON[k]
        attrs[ck] = fn(v)
    # identity
    eid = f"{brand.upper()}:{model}:{category}:pack{pack}"
    if category == "storage":
        eid += f":gb{attrs['capacity_gb']}"
    elif category == "cable":
        eid += f":mm{attrs['length_mm']}"
    return {
        "unresolved": None,
        "brand": brand,
        "model": model,
        "category": category,
        "pack_size": pack,
        "attributes": attrs,
        "entity_id": eid,
    }


# ---- group ----
entities = {}
uncertain = []
source_map = []

for r in rows:
    n = normalize_row(r)
    if n["unresolved"]:
        uncertain.append({
            "kind": "source",
            "source_sku": r["source_sku"],
            "source_row": r["row_id"],
            "reason": n["unresolved"],
        })
        source_map.append({
            "source_sku": r["source_sku"],
            "source_row": r["row_id"],
            "entity_id": None,
            "reason": n["unresolved"],
        })
        continue
    eid = n["entity_id"]
    e = entities.setdefault(eid, {
        "entity_id": eid,
        "brand": n["brand"],
        "model": n["model"],
        "category": n["category"],
        "pack_size": n["pack_size"],
        "sources": [],  # (sku, priority, attrs)
    })
    e["sources"].append({
        "source_sku": r["source_sku"],
        "source_row": r["row_id"],
        "source": r["source"],
        "priority": priority[r["source"]],
        "attributes": n["attributes"],
    })
    source_map.append({
        "source_sku": r["source_sku"],
        "source_row": r["row_id"],
        "entity_id": eid,
        "reason": None,
    })


# ---- resolve attributes/conflicts ----
out_entities = []
for eid, e in entities.items():
    srcs = e["sources"]
    skus = sorted(s["source_sku"] for s in srcs)
    attrs = {}
    conflicts = []
    keys = set()
    for s in srcs:
        keys.update(s["attributes"].keys())
    for k in sorted(keys):
        # gather normalized values across sources that have this attribute
        vals_by_src = [(s, s["attributes"][k]) for s in srcs if k in s["attributes"]]
        distinct = sorted({v for _, v in vals_by_src})
        # lowest priority present
        top = min(s["priority"] for s, _ in vals_by_src)
        top_vals = sorted({v for s, v in vals_by_src if s["priority"] == top})
        if len(distinct) == 1:
            chosen = distinct[0]
            attrs[k] = chosen
        else:
            # disagreement
            if len(top_vals) == 1:
                chosen = top_vals[0]
                resolution = "higher_priority"
                attrs[k] = chosen
            else:
                chosen = None
                resolution = "unresolved_tie"
                attrs[k] = None
                top_skus = sorted(s["source_sku"] for s, v in vals_by_src
                                  if s["priority"] == top)
                uncertain.append({
                    "kind": "attribute",
                    "entity_id": eid,
                    "attribute": k,
                    "source_skus": top_skus,
                })
            conflicts.append({
                "attribute": k,
                "observed_values": distinct,
                "chosen_value": chosen,
                "resolution": resolution,
                "source_skus": skus,
            })
    out_entities.append({
        "entity_id": eid,
        "brand": e["brand"],
        "model": e["model"],
        "category": e["category"],
        "pack_size": e["pack_size"],
        "attributes": attrs,
        "source_skus": skus,
        "conflicts": conflicts,
    })

# ---- report ----
print("=== ENTITIES ===")
for e in sorted(out_entities, key=lambda x: x["entity_id"]):
    print(json.dumps(e, sort_keys=True))
print()
print("=== SOURCE MAP ===")
for s in sorted(source_map, key=lambda x: x["source_sku"]):
    print(json.dumps(s, sort_keys=True))
print()
print("=== UNCERTAIN ===")
for u in uncertain:
    print(json.dumps(u, sort_keys=True))
print()
print("counts: entities=%d sources=%d mapped=%d unmapped=%d uncertain=%d" % (
    len(out_entities), len(source_map),
    sum(1 for s in source_map if s["entity_id"]),
    sum(1 for s in source_map if not s["entity_id"]),
    len(uncertain)))

# build the investigation artifact
row_by_sku = {r["source_sku"]: r["row_id"] for r in rows}
evidence = set()
for u in uncertain:
    if u["kind"] == "source":
        evidence.add(u["source_row"])
    else:
        for sku in u["source_skus"]:
            evidence.add(row_by_sku[sku])

report = {
    "findings": uncertain,
    "evidence_rows": sorted(evidence),
}
print()
print("=== REPORT ===")
print(json.dumps(report, sort_keys=True, indent=2))
json.dump({"kind": "json", "value": report}, open("/workspace/reference_work/report.json", "w"), indent=2)
