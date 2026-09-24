import json, re, sys

BASE = "materials/data"
rules = json.load(open(f"{BASE}/rules.json"))
rows = [json.loads(l) for l in open(f"{BASE}/catalog.jsonl") if l.strip()]
by_sku = {r["source_sku"]: r for r in rows}
scopes = json.load(open(f"{BASE}/scopes.json"))

BRAND_ALIAS = rules["brand_aliases"]
PRIORITY = rules["source_priority"]
ATTR_ALIAS = rules["attribute_aliases"]


def norm_brand(b):
    return BRAND_ALIAS.get(b, b)


def norm_model(m):
    if m is None:
        return None
    n = re.sub(r"[ \-]", "", m).upper()
    return n if n else None


def norm_pack(p):
    if p is None:
        return None
    if isinstance(p, int):
        return p
    s = str(p).strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d+)\s*pcs", s, re.I)
    if m:
        return int(m.group(1))
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None


def parse_num(v):
    """Return (number, unit) from strings like '100 W', '1.024 TB'."""
    m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*([A-Za-z]+)\s*", str(v))
    if not m:
        return None
    return float(m.group(1)), m.group(2).lower()


def norm_capacity(v):
    n, u = parse_num(v)
    if u == "tb":
        return int(round(n * 1000))
    if u == "gb":
        return int(round(n))
    raise ValueError(f"capacity unit {u}")


def norm_length(v):
    n, u = parse_num(v)
    if u == "m":
        return int(round(n * 1000))
    if u == "cm":
        return int(round(n * 10))
    if u == "mm":
        return int(round(n))
    raise ValueError(f"length unit {u}")


def norm_power(v):
    n, u = parse_num(v)
    if u == "w":
        return int(round(n))
    if u == "mw":
        return int(round(n / 1000))
    raise ValueError(f"power unit {u}")


def norm_connector(v):
    return ATTR_ALIAS.get(v, ATTR_ALIAS.get(str(v).lower(), v))


def norm_interface(v):
    return ATTR_ALIAS.get(v, ATTR_ALIAS.get(str(v).lower(), v))


def norm_color(v):
    return str(v).lower()


CANON = {
    "power": ("power_w", norm_power),
    "capacity": ("capacity_gb", norm_capacity),
    "length": ("length_mm", norm_length),
    "connector": ("connector", norm_connector),
    "interface": ("interface", norm_interface),
    "color": ("color", norm_color),
}

UNRESOLVED_REASONS = {"missing_model", "missing_pack_size"}


def build(scope_id):
    skus = scopes[scope_id]
    # ---- resolve identity for each source
    recs = {}
    for sku in skus:
        r = by_sku[sku]
        brand = norm_brand(r["brand"])
        model = norm_model(r["model"])
        pack = norm_pack(r["pack_size"])
        cat = r["category"]
        attrs = {}
        for k, v in (r["attributes"] or {}).items():
            if k in CANON:
                key, fn = CANON[k]
                attrs[key] = fn(v)
            else:
                attrs[k] = v
        if model is None:
            entity_id, reason = None, "missing_model"
        elif pack is None:
            entity_id, reason = None, "missing_pack_size"
        else:
            eid = f"{brand.upper()}:{model}:{cat}:pack{pack}"
            if cat == "storage":
                eid += f":gb{attrs['capacity_gb']}"
            elif cat == "cable":
                eid += f":mm{attrs['length_mm']}"
            entity_id, reason = eid, None
        recs[sku] = dict(row=r, brand=brand, model=model, pack=pack, cat=cat,
                         attrs=attrs, entity_id=entity_id, reason=reason)

    # ---- group
    groups = {}
    for sku, rec in recs.items():
        if rec["entity_id"] is not None:
            groups.setdefault(rec["entity_id"], []).append(sku)

    entities = []
    uncertain = []
    for eid, members in groups.items():
        members.sort()
        sample = recs[members[0]]
        # gather attributes across members
        attr_names = set()
        for s in members:
            attr_names.update(recs[s]["attrs"].keys())
        chosen = {}
        conflicts = []
        for a in sorted(attr_names):
            # collect (priority, value)
            obs = []
            for s in members:
                if a in recs[s]["attrs"]:
                    obs.append((PRIORITY[recs[s]["row"]["source"]], recs[s]["attrs"][a]))
            obs.sort(key=lambda t: t[0])
            top = min(p for p, _ in obs)
            top_vals = [v for p, v in obs if p == top]
            distinct = sorted({v for _, v in obs}, key=lambda x: (str(type(x)), x))
            if len(set(top_vals)) > 1:
                # unresolved tie at top priority
                chosen[a] = None
                top_sources = sorted(s for s in members
                                     if a in recs[s]["attrs"]
                                     and PRIORITY[recs[s]["row"]["source"]] == top)
                conflicts.append({
                    "attribute": a,
                    "observed_values": distinct,
                    "chosen_value": None,
                    "resolution": "unresolved_tie",
                    "source_skus": members,
                })
                uncertain.append({
                    "kind": "attribute",
                    "entity_id": eid,
                    "attribute": a,
                    "source_skus": top_sources,
                })
            else:
                chosen[a] = top_vals[0]
                if len(distinct) > 1:
                    conflicts.append({
                        "attribute": a,
                        "observed_values": distinct,
                        "chosen_value": chosen[a],
                        "resolution": "higher_priority",
                        "source_skus": members,
                    })
        entities.append({
            "entity_id": eid,
            "brand": sample["brand"],
            "model": sample["model"],
            "category": sample["cat"],
            "pack_size": sample["pack"],
            "attributes": chosen,
            "source_skus": members,
            "conflicts": conflicts,
        })

    source_map = []
    for sku in skus:
        rec = recs[sku]
        source_map.append({
            "source_sku": sku,
            "source_row": rec["row"]["row_id"],
            "entity_id": rec["entity_id"],
            "reason": rec["reason"],
        })
        if rec["entity_id"] is None:
            uncertain.append({
                "kind": "source",
                "source_sku": sku,
                "source_row": rec["row"]["row_id"],
                "reason": rec["reason"],
            })

    mapped = sum(1 for m in source_map if m["entity_id"] is not None)
    result = {
        "scope": scope_id,
        "entities": entities,
        "source_map": source_map,
        "uncertain": uncertain,
        "summary": {
            "entity_count": len(entities),
            "source_count": len(source_map),
            "mapped_source_count": mapped,
            "unmapped_source_count": len(source_map) - mapped,
            "uncertain_count": len(uncertain),
        },
    }
    return result


if __name__ == "__main__":
    scope = sys.argv[1] if len(sys.argv) > 1 else "normalize-retail-catalog"
    print(json.dumps(build(scope), indent=2))
