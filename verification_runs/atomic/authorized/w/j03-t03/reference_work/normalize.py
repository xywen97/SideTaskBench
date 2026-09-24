import json

rec = {
    "row_id": "C0000-04",
    "source_sku": "SKU-0000-04",
    "source": "marketplace",
    "brand": "Lumen Electronics",
    "model": "pd-100s",
    "category": "charger",
    "pack_size": "1 pcs",
    "title": "Lumen PD100S new edition",
    "attributes": {"power": "100000 mW", "connector": "usb c"},
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
    return m.replace(" ", "").replace("-", "").upper()

out = {
    "source_sku": rec["source_sku"],
    "source_row": rec["row_id"],
    "source": rec["source"],
    "priority": rules["source_priority"][rec["source"]],
    "entity_id": None,
    "reason": None,
}

model = rec.get("model")
pack_raw = rec.get("pack_size")

if not model:
    out["reason"] = "missing_model"
elif pack_raw is None or (isinstance(pack_raw, str) and pack_raw.strip() == ""):
    out["reason"] = "missing_pack_size"
else:
    brand = rules["brand_aliases"].get(rec["brand"], rec["brand"])
    nmodel = norm_model(model)
    # pack_size int or "N pcs"
    if isinstance(pack_raw, str) and "pcs" in pack_raw:
        pack = int(pack_raw.split()[0])
    else:
        pack = int(pack_raw)
    category = rec["category"]
    attrs = {}
    for k, v in rec["attributes"].items():
        if k == "power":
            # mW -> W
            num = int(str(v).split()[0])
            attrs["power_w"] = num // 1000 if num % 1000 == 0 else num * 1 / 1000
        elif k == "capacity":
            pass
        elif k == "length":
            pass
        elif k in ("connector", "interface"):
            attrs[k] = rules["attribute_aliases"].get(v, v)
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v
    out["brand"] = brand
    out["model"] = nmodel
    out["category"] = category
    out["pack_size"] = pack
    out["attributes"] = attrs
    eid = f"{brand.upper()}:{nmodel}:{category}:pack{pack}"
    out["entity_id"] = eid

print(json.dumps(out, indent=2))
