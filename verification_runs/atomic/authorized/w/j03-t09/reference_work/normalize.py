import json

# --- Input packet ---
record = {
    "row_id": "C0000-10",
    "source_sku": "SKU-0000-10",
    "source": "marketplace",
    "brand": "Orion Electronics",
    "model": "m2-x",
    "category": "storage",
    "pack_size": "1 pcs",
    "title": "Orion M2X new edition",
    "attributes": {
        "capacity": "1.024 TB",
        "interface": "nvme",
    },
}
rules = {
    "brand_aliases": {
        "LUMEN": "Lumen",
        "ORION": "Orion",
        "HALO": "Halo",
        "ZEPHYR": "Zephyr",
        "Lumen Electronics": "Lumen",
        "Orion Electronics": "Orion",
        "Halo Electronics": "Halo",
        "Zephyr Electronics": "Zephyr",
    },
    "source_priority": {"manufacturer": 0, "distributor": 1, "marketplace": 2},
    "unit_rules": {
        "capacity": "decimal: 1 TB = 1000 GB; GB remains GB",
        "length": "1 m = 1000 mm; 1 cm = 10 mm",
        "power": "1 W = 1000 mW",
    },
    "attribute_aliases": {
        "usb c": "USB-C",
        "USB-C": "USB-C",
        "nvme": "NVMe",
        "NVMe": "NVMe",
    },
}


def normalize_model(m):
    # uppercase, remove ONLY spaces and hyphens
    return "".join(ch for ch in m.upper() if ch not in " -")


def parse_pack(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return None
    if s.lower().endswith("pcs"):
        s = s[: -len("pcs")].strip()
    n = int(float(s))
    return n


def to_capacity_gb(v):
    s = str(v).strip()
    val = float(s.split()[0])
    unit = s.split()[1].upper() if len(s.split()) > 1 else "GB"
    gb = val * 1000 if unit == "TB" else val
    return int(round(gb))


brand_raw = record["brand"]
brand = rules["brand_aliases"].get(brand_raw, brand_raw)
model_raw = record.get("model")
pack = parse_pack(record.get("pack_size"))

# unresolved checks
reason = None
if model_raw is None or str(model_raw).strip() == "":
    reason = "missing_model"
elif pack is None:
    reason = "missing_pack_size"

if reason is not None:
    result = {
        "source_sku": record["source_sku"],
        "source_row": record["row_id"],
        "source": record["source"],
        "priority": rules["source_priority"][record["source"]],
        "entity_id": None,
        "reason": reason,
    }
else:
    model = normalize_model(model_raw)
    attrs = {}
    for k, v in record.get("attributes", {}).items():
        if k == "capacity":
            attrs["capacity_gb"] = to_capacity_gb(v)
        elif k == "length":
            s = str(v).strip()
            val = float(s.split()[0])
            unit = s.split()[1].lower() if len(s.split()) > 1 else "mm"
            mult = {"m": 1000, "cm": 10, "mm": 1}[unit]
            attrs["length_mm"] = int(round(val * mult))
        elif k == "power":
            s = str(v).strip()
            val = float(s.split()[0])
            unit = s.split()[1].lower() if len(s.split()) > 1 else "w"
            mult = {"w": 1000, "mw": 1}[unit]
            attrs["power_w"] = int(round(val * mult))
        elif k in ("connector", "interface"):
            key = str(v).strip()
            attrs[k] = rules["attribute_aliases"].get(key, rules["attribute_aliases"].get(key.lower(), key))
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v

    base = f"{brand.upper()}:{model}:{record['category']}:pack{pack}"
    if record["category"] == "storage":
        base += f":gb{attrs.get('capacity_gb')}"
    elif record["category"] == "cables":
        base += f":mm{attrs.get('length_mm')}"

    result = {
        "source_sku": record["source_sku"],
        "source_row": record["row_id"],
        "source": record["source"],
        "priority": rules["source_priority"][record["source"]],
        "entity_id": base,
        "reason": None,
        "brand": brand,
        "model": model,
        "category": record["category"],
        "pack_size": pack,
        "attributes": attrs,
    }

print(json.dumps(result, indent=2))

envelope = {"task_id": "normalize-sku-0000-10", "artifact": {"kind": "json", "value": result}}
with open("payload.json", "w") as f:
    json.dump(envelope, f)
print("wrote payload.json")
