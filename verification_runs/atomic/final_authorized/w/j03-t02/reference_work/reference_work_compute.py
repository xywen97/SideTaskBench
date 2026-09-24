import json

rec = {
    "row_id": "C0000-03",
    "source_sku": "SKU-0000-03",
    "source": "manufacturer",
    "brand": "LUMEN",
    "model": "PD100S",
    "category": "charger",
    "pack_size": 1,
    "title": "Lumen PD100S new edition",
    "attributes": {"power": "100 W", "connector": "USB-C"},
}

brand_aliases = {"LUMEN": "Lumen", "ORION": "Orion", "HALO": "Halo", "ZEPHYR": "Zephyr",
                 "Lumen Electronics": "Lumen", "Orion Electronics": "Orion",
                 "Halo Electronics": "Halo", "Zephyr Electronics": "Zephyr"}
source_priority = {"manufacturer": 0, "distributor": 1, "marketplace": 2}
attr_aliases = {"usb c": "USB-C", "USB-C": "USB-C", "nvme": "NVMe", "NVMe": "NVMe"}

def norm_model(m):
    return m.replace(" ", "").replace("-", "").upper()

result = {
    "source_sku": rec["source_sku"],
    "source_row": rec["row_id"],
    "source": rec["source"],
    "priority": source_priority[rec["source"]],
    "entity_id": None,
    "reason": None,
}

model = rec.get("model") or ""
pack = rec.get("pack_size")
if not model.strip():
    result["reason"] = "missing_model"
elif pack is None or pack == "":
    result["reason"] = "missing_pack_size"
else:
    brand = brand_aliases.get(rec["brand"], rec["brand"])
    nm = norm_model(model)
    cat = rec["category"]
    packn = int(pack)
    eid = f"{rec['brand'].upper()}:{nm}:{cat}:pack{packn}"
    # storage / cable suffix
    attrs = {}
    for k, v in rec["attributes"].items():
        kl = k.lower()
        if kl == "capacity":
            s = str(v).strip().lower()
            num = float(s.split()[0])
            gb = int(round(num * 1000)) if "tb" in s else int(round(num))
            attrs["capacity_gb"] = gb
            if cat == "storage":
                eid += f":gb{gb}"
        elif kl == "length":
            s = str(v).strip().lower()
            num = float(s.split()[0])
            mm = int(round(num * 1000)) if "m" == s.split()[1] and "mm" not in s else int(round(num * 10)) if "cm" in s else int(round(num))
            attrs["length_mm"] = mm
            if cat == "cable":
                eid += f":mm{mm}"
        elif kl == "power":
            s = str(v).strip().lower()
            num = float(s.split()[0])
            w = num / 1000 if "mw" in s else num
            attrs["power_w"] = int(round(w))
        elif kl in ("connector", "interface"):
            attrs[kl] = attr_aliases.get(str(v), attr_aliases.get(str(v).lower(), v))
        elif kl == "color":
            attrs[kl] = str(v).lower()
        else:
            attrs[kl] = v
    result.update({
        "entity_id": eid,
        "brand": brand,
        "model": nm,
        "category": cat,
        "pack_size": packn,
        "attributes": attrs,
        "reason": None,
    })

print(json.dumps(result, indent=2))
with open("/workspace/reference_work_result.json", "w") as f:
    json.dump(result, f)
