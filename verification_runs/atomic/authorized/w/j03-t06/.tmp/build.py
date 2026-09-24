import json, re

rec = {
    "row_id": "C0000-07",
    "source_sku": "SKU-0000-07",
    "source": "manufacturer",
    "brand": "ORION",
    "model": "M2X",
    "category": "storage",
    "pack_size": 1,
    "title": "Orion M2X new edition",
    "attributes": {"capacity": "1000 GB", "interface": "NVMe"},
}

brand_aliases = {"LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr",
"Lumen Electronics":"Lumen","Orion Electronics":"Orion","Halo Electronics":"Halo","Zephyr Electronics":"Zephyr"}
source_priority = {"manufacturer":0,"distributor":1,"marketplace":2}
attribute_aliases = {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"}

brand = brand_aliases.get(rec["brand"], rec["brand"])
model = re.sub(r'[ -]', '', rec["model"].upper())
category = rec["category"]
pack_size = rec["pack_size"]

# missing checks
reason = None
if not rec["model"]:
    reason = "missing_model"
elif pack_size is None or pack_size == "":
    reason = "missing_pack_size"

priority = source_priority[rec["source"]]
base = {"source_sku":rec["source_sku"],"source_row":rec["row_id"],"source":rec["source"],
        "priority":priority,"entity_id":None,"reason":reason}

if reason is not None:
    result = base
else:
    attrs = {}
    cap_gb = None
    for k,v in rec["attributes"].items():
        if k == "capacity":
            m = re.match(r'^([\d.]+)\s*(TB|GB)$', str(v).strip(), re.I)
            num = float(m.group(1)); unit = m.group(2).upper()
            gb = num*1000 if unit == "TB" else num
            attrs["capacity_gb"] = int(round(gb))
            cap_gb = int(round(gb))
        elif k in ("length",):
            m = re.match(r'^([\d.]+)\s*(m|cm|mm)$', str(v).strip(), re.I)
            num=float(m.group(1)); unit=m.group(2).lower()
            mm = {"m":1000,"cm":10,"mm":1}[unit]*num
            attrs["length_mm"]=int(round(mm))
        elif k == "power":
            m = re.match(r'^([\d.]+)\s*(mW|W)$', str(v).strip(), re.I)
            num=float(m.group(1)); unit=m.group(2)
            w = num*0.001 if unit.lower()=="mw" else num
            attrs["power_w"]=int(round(w))
        elif k in ("interface","connector"):
            attrs[k] = attribute_aliases.get(str(v), attribute_aliases.get(str(v).lower(), v))
        elif k == "color":
            attrs[k] = str(v).lower()
        else:
            attrs[k] = v
    eid = f"{brand.upper()}:{model}:{category}:pack{pack_size}"
    if category == "storage":
        eid += f":gb{cap_gb}"
    elif category == "cables":
        eid += f":mm{attrs.get('length_mm')}"
    result = dict(base)
    result.update({"entity_id":eid,"brand":brand,"model":model,"category":category,
                   "pack_size":pack_size,"attributes":attrs})

print(json.dumps(result, indent=2))
