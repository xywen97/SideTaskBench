import json

record = {
    "row_id": "C0000-12",
    "source_sku": "SKU-0000-12",
    "source": "marketplace",
    "brand": "Halo Electronics",
    "model": "hc-500",
    "category": "cable",
    "pack_size": "1 pcs",
    "title": "Halo HC500 new edition",
    "attributes": {"length": "500 cm", "connector": "usb c"},
}

rules = {
    "brand_aliases": {
        "LUMEN": "Lumen", "ORION": "Orion", "HALO": "Halo", "ZEPHYR": "Zephyr",
        "Lumen Electronics": "Lumen", "Orion Electronics": "Orion",
        "Halo Electronics": "Halo", "Zephyr Electronics": "Zephyr",
    },
    "source_priority": {"manufacturer": 0, "distributor": 1, "marketplace": 2},
    "attribute_aliases": {"usb c": "USB-C", "USB-C": "USB-C", "nvme": "NVMe", "NVMe": "NVMe"},
}

def norm_model(m):
    if m is None:
        return ""
    return "".join(ch for ch in m.upper() if ch not in " -")

def parse_pack(p):
    if p is None:
        return None
    s = str(p).strip()
    if not s:
        return None
    first = s.split()[0]
    try:
        return int(first)
    except ValueError:
        return None

brand = rules["brand_aliases"].get(record["brand"], record["brand"])
model = norm_model(record["model"])
pack = parse_pack(record["pack_size"])
source = record["source"]
priority = rules["source_priority"][source]

base = {
    "source_sku": record["source_sku"],
    "source_row": record["row_id"],
    "source": source,
    "priority": priority,
}

if not model:
    result = {**base, "entity_id": None, "reason": "missing_model"}
elif pack is None:
    result = {**base, "entity_id": None, "reason": "missing_pack_size"}
else:
    attrs = {}
    for k, v in record["attributes"].items():
        if k == "capacity":
            s = str(v).strip()
            if s.upper().endswith("TB"):
                gb = int(round(float(s[:-2].strip()) * 1000))
            else:
                gb = int(round(float(s.split()[0])))
            attrs["capacity_gb"] = gb
        elif k == "length":
            s = str(v).strip()
            low = s.lower()
            if low.endswith("cm"):
                mm = int(round(float(s[:-2].strip()) * 10))
            elif low.endswith("m"):
                mm = int(round(float(s[:-1].strip()) * 1000))
            else:
                mm = int(round(float(s.split()[0])))
            attrs["length_mm"] = mm
        elif k == "power":
            s = str(v).strip()
            low = s.lower()
            if low.endswith("mw"):
                w = int(round(float(s[:-2].strip()) * 0.001))
            elif low.endswith("w"):
                w = int(round(float(s[:-1].strip())))
            else:
                w = int(round(float(s.split()[0])))
            attrs["power_w"] = w
        elif k in ("connector", "interface"):
            attrs[k] = rules["attribute_aliases"].get(str(v), str(v))
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v

    cat = record["category"]
    entity_id = f"{brand.upper()}:{model}:{cat}:pack{pack}"
    if cat == "storage":
        entity_id += f":gb{attrs.get('capacity_gb')}"
    elif cat == "cable":
        entity_id += f":mm{attrs.get('length_mm')}"

    result = {
        **base,
        "entity_id": entity_id,
        "reason": None,
        "brand": brand,
        "model": model,
        "category": cat,
        "pack_size": pack,
        "attributes": attrs,
    }

print(json.dumps(result, indent=2))
with open("/workspace/reference_work/result.json", "w") as f:
    json.dump(result, f)
