import json, re

record = {
    "row_id": "C0000-14",
    "source_sku": "SKU-0000-14",
    "source": "marketplace",
    "brand": "Halo Electronics",
    "model": "hc-500s",
    "category": "cable",
    "pack_size": "1 pcs",
    "title": "Halo HC500S new edition",
    "attributes": {"length": "500 cm", "connector": "usb c"},
}
rules = {
    "brand_aliases": {
        "LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr",
        "Lumen Electronics":"Lumen","Orion Electronics":"Orion",
        "Halo Electronics":"Halo","Zephyr Electronics":"Zephyr"},
    "source_priority": {"manufacturer":0,"distributor":1,"marketplace":2},
    "attribute_aliases": {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"},
}

src = record["source"]
result = {
    "source_sku": record["source_sku"],
    "source_row": record["row_id"],
    "source": src,
    "priority": rules["source_priority"][src],
}

model_raw = record.get("model")
model = re.sub(r"[\s-]", "", model_raw).upper() if model_raw else ""
pack_raw = record.get("pack_size")

if not model:
    result.update({"entity_id": None, "reason": "missing_model"}); print(json.dumps(result)); raise SystemExit
if pack_raw is None or str(pack_raw).strip() == "":
    result.update({"entity_id": None, "reason": "missing_pack_size"}); print(json.dumps(result)); raise SystemExit

m = re.search(r"\d+", str(pack_raw))
pack_size = int(m.group()) if m else None

brand = rules["brand_aliases"].get(record["brand"], record["brand"])
category = record["category"]

attrs = {}
for k, v in record["attributes"].items():
    if k == "length":
        num = float(re.search(r"-?\d+(\.\d+)?", str(v)).group())
        s = str(v).lower()
        mm = num*1000 if ("m" in s and "cm" not in s and "mm" not in s) else (num*10 if "cm" in s else num)
        attrs["length_mm"] = int(round(mm))
    elif k == "capacity":
        num = float(re.search(r"-?\d+(\.\d+)?", str(v)).group())
        s = str(v).lower()
        gb = num*1000 if "tb" in s else num
        attrs["capacity_gb"] = int(round(gb))
    elif k == "power":
        num = float(re.search(r"-?\d+(\.\d+)?", str(v)).group())
        s = str(v).lower()
        w = num*0.001 if "mw" in s else num
        attrs["power_w"] = int(round(w))
    elif k in ("connector", "interface"):
        attrs[k] = rules["attribute_aliases"].get(v, v)
    elif k == "color":
        attrs[k] = str(v).lower()
    else:
        attrs[k] = v

entity_id = f"{brand.upper()}:{model}:{category}:pack{pack_size}"
if category == "storage":
    entity_id += f":gb{attrs.get('capacity_gb')}"
elif category == "cable" and "length_mm" in attrs:
    entity_id += f":mm{attrs['length_mm']}"

result.update({
    "entity_id": entity_id,
    "reason": None,
    "brand": brand,
    "model": model,
    "category": category,
    "pack_size": pack_size,
    "attributes": attrs,
})
print(json.dumps(result, indent=2))
json.dump(result, open("reference_work/result.json","w"), indent=2)
