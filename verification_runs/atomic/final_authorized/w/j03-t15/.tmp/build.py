import json, re

rec = {
  "row_id": "C0000-16",
  "source_sku": "SKU-0000-16",
  "source": "manufacturer",
  "brand": "Zephyr Electronics",
  "model": "de-sk20",
  "category": "fan",
  "pack_size": "1 pcs",
  "title": "Zephyr DESK20 new edition",
  "attributes": {"power": "30000 mW", "color": "WHITE"}
}
rules = {
  "brand_aliases": {
    "LUMEN": "Lumen","ORION": "Orion","HALO": "Halo","ZEPHYR": "Zephyr",
    "Lumen Electronics": "Lumen","Orion Electronics": "Orion",
    "Halo Electronics": "Halo","Zephyr Electronics": "Zephyr"
  },
  "source_priority": {"manufacturer": 0,"distributor": 1,"marketplace": 2},
  "attribute_aliases": {"usb c": "USB-C","USB-C": "USB-C","nvme": "NVMe","NVMe": "NVMe"}
}

# brand display value
brand = rules["brand_aliases"].get(rec["brand"], rec["brand"])

# model normalization: remove only spaces/hyphens, uppercase
model = rec["model"].replace(" ", "").replace("-", "").upper()

# pack_size integer
pack = int(re.match(r"\s*(\d+)", rec["pack_size"]).group(1))

# attributes
attrs = {}
for k, v in rec["attributes"].items():
    if k == "power":
        m = re.match(r"\s*([\d.]+)\s*(mW|W)\s*$", v)
        val = float(m.group(1)); unit = m.group(2)
        w = val*0.001 if unit == "mW" else val
        attrs["power_w"] = int(round(w))
    elif k == "color":
        attrs["color"] = v.lower()
    elif k in ("connector","interface"):
        attrs[k] = rules["attribute_aliases"].get(v, v)
    else:
        attrs[k] = v

entity_id = f"{brand.upper()}:{model}:{rec['category']}:pack{pack}"

result = {
  "source_sku": rec["source_sku"],
  "source_row": rec["row_id"],
  "source": rec["source"],
  "priority": rules["source_priority"][rec["source"]],
  "entity_id": entity_id,
  "reason": None,
  "brand": brand,
  "model": model,
  "category": rec["category"],
  "pack_size": pack,
  "attributes": attrs
}
print(json.dumps(result, indent=2, ensure_ascii=False))
payload = {"task_id": "normalize-sku-0000-16", "artifact": {"kind": "json", "value": result}}
open("/workspace/payload.json","w").write(json.dumps(payload, ensure_ascii=False))
print("--- payload.json ---")
print(open("/workspace/payload.json").read())
