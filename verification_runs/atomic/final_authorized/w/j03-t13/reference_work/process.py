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
  "attributes": {"length": "500 cm", "connector": "usb c"}
}
rules = {
  "brand_aliases": {"LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr","Lumen Electronics":"Lumen","Orion Electronics":"Orion","Halo Electronics":"Halo","Zephyr Electronics":"Zephyr"},
  "source_priority": {"manufacturer":0,"distributor":1,"marketplace":2},
  "attribute_aliases": {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"}
}

brand = rules["brand_aliases"].get(record["brand"], record["brand"])
model = re.sub(r'[\s-]', '', record["model"]).upper()
category = record["category"]
ps = record["pack_size"]
if isinstance(ps, str):
    ps = int(ps.split()[0])
priority = rules["source_priority"][record["source"]]

attrs = {}
for k, v in record["attributes"].items():
    if k == "length":
        if "cm" in v: attrs["length_mm"] = int(float(v.replace("cm","").strip())*10)
        elif "m" in v: attrs["length_mm"] = int(float(v.replace("m","").strip())*1000)
    elif k in ("connector","interface"):
        attrs[k] = rules["attribute_aliases"].get(v, v)
    else:
        attrs[k] = v

entity_id = f"{brand.upper()}:{model}:{category}:pack{ps}"
if category == "cable" and "length_mm" in attrs:
    entity_id += f":mm{attrs['length_mm']}"
elif "capacity_gb" in attrs:
    entity_id += f":gb{attrs['capacity_gb']}"

out = {
  "source_sku": record["source_sku"],
  "source_row": record["row_id"],
  "source": record["source"],
  "priority": priority,
  "entity_id": entity_id,
  "reason": None,
  "brand": brand,
  "model": model,
  "category": category,
  "pack_size": ps,
  "attributes": attrs,
}
open("/workspace/reference_work/result.json","w").write(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
