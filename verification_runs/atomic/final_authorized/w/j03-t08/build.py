import json

rec = {
  "row_id": "C0000-09",
  "source_sku": "SKU-0000-09",
  "source": "manufacturer",
  "brand": "ORION",
  "model": "M2X",
  "category": "storage",
  "pack_size": 1,
  "title": "Orion M2X new edition",
  "attributes": {"capacity": "1024 GB", "interface": "NVMe"}
}

brand_aliases = {"LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr",
  "Lumen Electronics":"Lumen","Orion Electronics":"Orion","Halo Electronics":"Halo","Zephyr Electronics":"Zephyr"}
source_priority = {"manufacturer":0,"distributor":1,"marketplace":2}
attribute_aliases = {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"}

def norm_model(m):
    return "".join(ch for ch in m if ch not in " -").upper()

brand = brand_aliases.get(rec["brand"], rec["brand"])
model = norm_model(rec["model"])
category = rec["category"]
pack_size = rec["pack_size"]

attrs = {}
for k, v in rec["attributes"].items():
    if k == "capacity":
        s = str(v).strip()
        if s.upper().endswith("TB"):
            attrs["capacity_gb"] = int(float(s[:-2].strip()) * 1000)
        elif s.upper().endswith("GB"):
            attrs["capacity_gb"] = int(float(s[:-2].strip()))
        else:
            attrs["capacity_gb"] = int(float(s))
    elif k == "interface":
        attrs["interface"] = attribute_aliases.get(str(v), str(v))
    else:
        attrs[k] = v

entity = f"{brand.upper()}:{model}:{category}:pack{pack_size}"
if category == "storage":
    entity += f":gb{attrs['capacity_gb']}"

value = {
  "source_sku": rec["source_sku"],
  "source_row": rec["row_id"],
  "source": rec["source"],
  "priority": source_priority[rec["source"]],
  "entity_id": entity,
  "reason": None,
  "brand": brand,
  "model": model,
  "category": category,
  "pack_size": pack_size,
  "attributes": attrs,
}

payload = {"task_id": "normalize-sku-0000-09", "artifact": {"kind": "json", "value": value}}
with open("/workspace/payload.json", "w") as f:
    json.dump(payload, f)
print(json.dumps(payload, indent=2))
