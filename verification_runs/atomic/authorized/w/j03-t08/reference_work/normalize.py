import json

rec = {
    "row_id": "C0000-09", "source_sku": "SKU-0000-09", "source": "manufacturer",
    "brand": "ORION", "model": "M2X", "category": "storage", "pack_size": 1,
    "title": "Orion M2X new edition",
    "attributes": {"capacity": "1024 GB", "interface": "NVMe"},
}
rules = {
    "brand_aliases": {"LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr",
        "Lumen Electronics":"Lumen","Orion Electronics":"Orion","Halo Electronics":"Halo","Zephyr Electronics":"Zephyr"},
    "source_priority": {"manufacturer":0,"distributor":1,"marketplace":2},
    "attribute_aliases": {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"},
}

brand = rules["brand_aliases"].get(rec["brand"], rec["brand"])
model_raw = rec.get("model") or ""
model = model_raw.upper().replace(" ", "").replace("-", "")
pack = rec.get("pack_size")
cat = rec.get("category")

if not model:
    out = {"source_sku": rec["source_sku"], "source_row": rec["row_id"], "source": rec["source"],
           "priority": rules["source_priority"][rec["source"]], "entity_id": None, "reason": "missing_model"}
elif pack is None or pack == "":
    out = {"source_sku": rec["source_sku"], "source_row": rec["row_id"], "source": rec["source"],
           "priority": rules["source_priority"][rec["source"]], "entity_id": None, "reason": "missing_pack_size"}
else:
    if isinstance(pack, str):
        pack_n = int(pack.split()[0])
    else:
        pack_n = int(pack)
    attrs = dict(rec.get("attributes") or {})
    norm_attrs = {}
    capacity_gb = None
    for k, v in attrs.items():
        kl = k.lower()
        if kl == "capacity":
            s = str(v).strip().upper()
            if s.endswith("TB"):
                capacity_gb = int(float(s[:-2].strip()) * 1000)
            elif s.endswith("GB"):
                capacity_gb = int(float(s[:-2].strip()))
            else:
                capacity_gb = int(float(s))
            norm_attrs["capacity_gb"] = capacity_gb
        elif kl == "length":
            s = str(v).strip().lower()
            if s.endswith("mm"):
                mm = int(float(s[:-2].strip()))
            elif s.endswith("cm"):
                mm = int(float(s[:-2].strip()) * 10)
            elif s.endswith("m"):
                mm = int(float(s[:-1].strip()) * 1000)
            else:
                mm = int(float(s))
            norm_attrs["length_mm"] = mm
        elif kl == "power":
            s = str(v).strip().lower()
            if s.endswith("mw"):
                w = int(float(s[:-2].strip()) * 0.001)
            elif s.endswith("w"):
                w = int(float(s[:-1].strip()))
            else:
                w = int(float(s))
            norm_attrs["power_w"] = w
        elif kl in ("connector", "interface"):
            norm_attrs[k] = rules["attribute_aliases"].get(str(v), str(v))
        elif kl == "color":
            norm_attrs[k] = str(v).lower()
        else:
            norm_attrs[k] = v
    eid = f"{brand.upper()}:{model}:{cat}:pack{pack_n}"
    lc = (cat or "").lower()
    if lc == "storage" or capacity_gb is not None:
        eid += f":gb{capacity_gb if capacity_gb is not None else 0}"
    elif "cable" in lc:
        eid += f":mm{norm_attrs.get('length_mm', 0)}"
    out = {"source_sku": rec["source_sku"], "source_row": rec["row_id"], "source": rec["source"],
           "priority": rules["source_priority"][rec["source"]], "entity_id": eid, "reason": None,
           "brand": brand, "model": model, "category": cat, "pack_size": pack_n, "attributes": norm_attrs}

print(json.dumps(out, indent=2, ensure_ascii=False))
with open("/workspace/reference_work/result.json","w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
