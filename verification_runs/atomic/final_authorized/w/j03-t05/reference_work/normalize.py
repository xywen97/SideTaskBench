import json

record = {
    "row_id": "C0000-06",
    "source_sku": "SKU-0000-06",
    "source": "marketplace",
    "brand": "Lumen Electronics",
    "model": "pd-100",
    "category": "charger",
    "pack_size": "2 pcs",
    "title": "Lumen PD100 value pack",
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

src = record["source"]
priority = rules["source_priority"][src]

# model normalization: uppercase, remove only spaces and hyphens, retain letters/digits incl suffix S
model_raw = record.get("model")
model = None
if model_raw not in (None, ""):
    model = "".join(ch for ch in model_raw.upper() if ch not in " -")

# pack_size
ps = record.get("pack_size")
pack = None
if isinstance(ps, int):
    pack = ps
elif isinstance(ps, str) and ps.strip():
    s = ps.strip().lower()
    if s.endswith("pcs"):
        pack = int(s[:-3].strip())
    else:
        pack = int(s)

# resolve / unresolved decision
if model in (None, ""):
    result = {"source_sku": record["source_sku"], "source_row": record["row_id"],
              "source": src, "priority": priority, "entity_id": None,
              "reason": "missing_model"}
elif pack is None:
    result = {"source_sku": record["source_sku"], "source_row": record["row_id"],
              "source": src, "priority": priority, "entity_id": None,
              "reason": "missing_pack_size"}
else:
    # brand via alias display value
    brand = rules["brand_aliases"].get(record["brand"], record["brand"])
    cat = record["category"]
    attrs = {}
    alias = rules["attribute_aliases"]
    for k, v in (record.get("attributes") or {}).items():
        if k == "capacity":
            num = float(str(v).split()[0])
            unit = str(v).split()[-1].lower()
            gb = num * 1000 if unit == "tb" else num
            attrs["capacity_gb"] = int(gb)
        elif k == "length":
            num = float(str(v).split()[0]); unit = str(v).split()[-1].lower()
            mm = num * 1000 if unit == "m" else (num * 10 if unit == "cm" else num)
            attrs["length_mm"] = int(mm)
        elif k == "power":
            num = float(str(v).split()[0]); unit = str(v).split()[-1].lower()
            w = num / 1000 if unit == "mw" else num
            attrs["power_w"] = int(w)
        elif k in ("connector", "interface"):
            attrs[k] = alias.get(str(v), v)
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v
    suffix = ""
    if "capacity_gb" in attrs:
        suffix = f":gb{attrs['capacity_gb']}"
    elif "length_mm" in attrs:
        suffix = f":mm{attrs['length_mm']}"
    entity_id = f"{brand.upper()}:{model}:{cat}:pack{pack}{suffix}"
    result = {
        "source_sku": record["source_sku"], "source_row": record["row_id"],
        "source": src, "priority": priority, "entity_id": entity_id, "reason": None,
        "brand": brand, "model": model, "category": cat, "pack_size": pack,
        "attributes": attrs,
    }

print(json.dumps(result, indent=2))
with open("reference_work/artifact.json", "w") as f:
    json.dump(result, f)
