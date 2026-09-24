import json

rec = {
    "row_id": "C0000-10",
    "source_sku": "SKU-0000-10",
    "source": "marketplace",
    "brand": "Orion Electronics",
    "model": "m2-x",
    "category": "storage",
    "pack_size": "1 pcs",
    "title": "Orion M2X new edition",
    "attributes": {"capacity": "1.024 TB", "interface": "nvme"},
}

brand_aliases = {
    "LUMEN": "Lumen", "ORION": "Orion", "HALO": "Halo", "ZEPHYR": "Zephyr",
    "Lumen Electronics": "Lumen", "Orion Electronics": "Orion",
    "Halo Electronics": "Halo", "Zephyr Electronics": "Zephyr",
}
source_priority = {"manufacturer": 0, "distributor": 1, "marketplace": 2}
attribute_aliases = {"usb c": "USB-C", "USB-C": "USB-C", "nvme": "NVMe", "NVMe": "NVMe"}

def norm_model(m):
    if m is None:
        return ""
    return "".join(ch for ch in m if ch not in " -").upper()

def parse_pack(p):
    if p is None:
        return None
    if isinstance(p, int):
        return p
    s = str(p).strip()
    if s == "":
        return None
    # "N pcs"
    num = s.split()[0]
    try:
        return int(num)
    except ValueError:
        try:
            return int(float(num))
        except ValueError:
            return None

brand = brand_aliases.get(rec["brand"], rec["brand"])
model = norm_model(rec["model"])
category = rec["category"]
pack_size = parse_pack(rec["pack_size"])

base = {
    "source_sku": rec["source_sku"],
    "source_row": rec["row_id"],
    "source": rec["source"],
    "priority": source_priority[rec["source"]],
}

if not model:
    result = {**base, "entity_id": None, "reason": "missing_model"}
elif pack_size is None:
    result = {**base, "entity_id": None, "reason": "missing_pack_size"}
else:
    attrs = {}
    for k, v in rec["attributes"].items():
        if k == "capacity":
            s = str(v).strip().upper()
            if s.endswith("TB"):
                gb = int(round(float(s[:-2].strip()) * 1000))
            elif s.endswith("GB"):
                gb = int(round(float(s[:-2].strip())))
            else:
                gb = int(round(float(s)))
            attrs["capacity_gb"] = gb
        elif k == "length":
            s = str(v).strip().lower()
            if s.endswith("mm"):
                mm = int(round(float(s[:-2].strip())))
            elif s.endswith("cm"):
                mm = int(round(float(s[:-2].strip()) * 10))
            elif s.endswith("m"):
                mm = int(round(float(s[:-1].strip()) * 1000))
            else:
                mm = int(round(float(s)))
            attrs["length_mm"] = mm
        elif k == "power":
            s = str(v).strip().lower()
            if s.endswith("mw"):
                w = int(round(float(s[:-2].strip()) * 0.001))
            elif s.endswith("w"):
                w = int(round(float(s[:-1].strip())))
            else:
                w = int(round(float(s)))
            attrs["power_w"] = w
        elif k in ("connector", "interface"):
            attrs[k] = attribute_aliases.get(str(v).strip(), str(v).strip())
        elif k == "color":
            attrs["color"] = str(v).strip().lower()
        else:
            attrs[k] = v

    eid = f"{brand.upper()}:{model}:{category}:pack{pack_size}"
    if category == "storage":
        eid += f":gb{attrs['capacity_gb']}"
    elif category == "cable":
        eid += f":mm{attrs['length_mm']}"

    result = {
        **base,
        "entity_id": eid,
        "reason": None,
        "brand": brand,
        "model": model,
        "category": category,
        "pack_size": pack_size,
        "attributes": attrs,
    }

print(json.dumps(result, indent=2, ensure_ascii=False))
