import json, re

record = {
    "row_id": "C0000-01",
    "source_sku": "SKU-0000-01",
    "source": "manufacturer",
    "brand": "LUMEN",
    "model": "PD100",
    "category": "charger",
    "pack_size": 1,
    "title": "Lumen PD100 new edition",
    "attributes": {"power": "100 W", "connector": "USB-C"},
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
        return None
    return re.sub(r"[ -]", "", m).upper()

brand_raw = record.get("brand")
brand = rules["brand_aliases"].get(brand_raw, brand_raw)
model = norm_model(record.get("model"))
pack = record.get("pack_size")
category = record.get("category")

priority = rules["source_priority"][record["source"]]
base = {"source_sku": record["source_sku"], "source_row": record["row_id"],
        "source": record["source"], "priority": priority}

if not model:
    out = dict(base, entity_id=None, reason="missing_model")
elif pack is None or pack == "":
    out = dict(base, entity_id=None, reason="missing_pack_size")
else:
    attrs = {}
    for k, v in (record.get("attributes") or {}).items():
        kl = k.lower()
        if kl == "power":
            m = re.match(r"^\s*([0-9.]+)\s*(W|mW)?\s*$", str(v))
            val = float(m.group(1)); unit = m.group(2) or "W"
            attrs["power_w"] = int(round(val * (0.001 if unit == "mW" else 1.0)))
        elif kl == "connector" or kl == "interface":
            key = str(v).lower()
            attrs[k] = rules["attribute_aliases"].get(str(v), rules["attribute_aliases"].get(key, v))
        else:
            attrs[k] = v
    brand_upper = (brand or "").upper()
    entity_id = f"{brand_upper}:{model}:{category}:pack{int(pack)}"
    out = dict(base, entity_id=entity_id, reason=None, brand=brand, model=model,
               category=category, pack_size=int(pack), attributes=attrs)

print(json.dumps(out, ensure_ascii=False))
with open("reference_work/result.json", "w") as f:
    json.dump(out, f, ensure_ascii=False)
