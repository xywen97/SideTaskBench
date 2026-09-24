import json, re

record = {
    "row_id": "C0000-03",
    "source_sku": "SKU-0000-03",
    "source": "manufacturer",
    "brand": "LUMEN",
    "model": "PD100S",
    "category": "charger",
    "pack_size": 1,
    "title": "Lumen PD100S new edition",
    "attributes": {
        "power": "100 W",
        "connector": "USB-C"
    }
}

rules = {
    "brand_aliases": {
        "LUMEN": "Lumen", "ORION": "Orion", "HALO": "Halo", "ZEPHYR": "Zephyr",
        "Lumen Electronics": "Lumen", "Orion Electronics": "Orion",
        "Halo Electronics": "Halo", "Zephyr Electronics": "Zephyr"
    },
    "source_priority": {"manufacturer": 0, "distributor": 1, "marketplace": 2},
    "attribute_aliases": {"usb c": "USB-C", "USB-C": "USB-C", "nvme": "NVMe", "NVMe": "NVMe"},
}

def norm_model(m):
    if m is None:
        return None
    return re.sub(r'[ -]', '', m).upper()

out = {
    "source_sku": record["source_sku"],
    "source_row": record["row_id"],
    "source": record["source"],
    "priority": rules["source_priority"][record["source"]],
    "entity_id": None,
    "reason": None,
}

model = norm_model(record.get("model"))
pack = record.get("pack_size")

if not model:
    out["reason"] = "missing_model"
elif pack is None or pack == "":
    out["reason"] = "missing_pack_size"
else:
    brand = rules["brand_aliases"].get(record["brand"], record["brand"])
    out["brand"] = brand
    out["model"] = model
    out["category"] = record["category"]
    out["pack_size"] = pack

    attrs = {}
    for k, v in (record.get("attributes") or {}).items():
        if k == "power":
            # parse "100 W", "500 mW"
            m = re.match(r'^\s*([\d.]+)\s*(mW|W)?\s*$', str(v))
            num = float(m.group(1)); unit = (m.group(2) or "W")
            no = num/1000.0 if unit == "mW" else num
            attrs["power_w"] = int(no)
        elif k == "capacity":
            m = re.match(r'^\s*([\d.]+)\s*(TB|GB)?\s*$', str(v))
            num = float(m.group(1)); unit = (m.group(2) or "GB")
            attrs["capacity_gb"] = int(num*1000 if unit == "TB" else num)
        elif k == "length":
            m = re.match(r'^\s*([\d.]+)\s*(m|cm|mm)?\s*$', str(v))
            num = float(m.group(1)); unit = (m.group(2) or "mm")
            factor = {"m":1000, "cm":10, "mm":1}[unit]
            attrs["length_mm"] = int(num*factor)
        elif k in ("connector", "interface"):
            vv = rules["attribute_aliases"].get(v, rules["attribute_aliases"].get(str(v).lower(), v))
            attrs[k] = vv
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v
    out["attributes"] = attrs

    brand_upper = brand.upper()
    eid = f"{brand_upper}:{model}:{record['category']}:pack{pack}"
    if record["category"] == "storage":
        # append :gbN - use capacity_gb
        eid += f":gb{attrs.get('capacity_gb')}"
    elif record["category"] == "cable":
        eid += f":mm{attrs.get('length_mm')}"
    out["entity_id"] = eid

print(json.dumps(out, ensure_ascii=False, indent=2))

payload = {"task_id": "normalize-sku-0000-03", "artifact": {"kind": "json", "value": out}}
with open("/workspace/payload.json", "w") as f:
    json.dump(payload, f, ensure_ascii=False)
print("--- payload written ---")
