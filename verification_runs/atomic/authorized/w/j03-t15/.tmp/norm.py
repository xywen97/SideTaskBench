import json, re

record = {
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
    "brand_aliases": {"LUMEN":"Lumen","ORION":"Orion","HALO":"Halo","ZEPHYR":"Zephyr",
        "Lumen Electronics":"Lumen","Orion Electronics":"Orion","Halo Electronics":"Halo",
        "Zephyr Electronics":"Zephyr"},
    "source_priority": {"manufacturer":0,"distributor":1,"marketplace":2},
    "unit_rules": {"capacity":"decimal: 1 TB = 1000 GB; GB remains GB",
        "length":"1 m = 1000 mm; 1 cm = 10 mm","power":"1 W = 1000 mW"},
    "attribute_aliases": {"usb c":"USB-C","USB-C":"USB-C","nvme":"NVMe","NVMe":"NVMe"}
}

def norm_model(m):
    if m is None: return ""
    return re.sub(r'[ \-]', '', m).upper()

def parse_pack(p):
    if p is None: return None
    if isinstance(p, int): return p
    s = str(p).strip()
    if s == "": return None
    mm = re.match(r'^(\d+)\s*pcs$', s)
    if mm: return int(mm.group(1))
    if re.match(r'^\d+$', s): return int(s)
    return None

def norm_attrs(attrs):
    out = {}
    for k, v in attrs.items():
        kl = str(k).lower().strip()
        if kl == "capacity":
            s = str(v).strip()
            num = float(re.match(r'^([\d.]+)', s).group(1))
            out["capacity_gb"] = int(round(num * 1000)) if s.upper().endswith("TB") else int(round(num))
        elif kl == "length":
            s = str(v).strip()
            num = float(re.match(r'^([\d.]+)', s).group(1))
            if s.endswith("cm"): out["length_mm"] = int(round(num*10))
            elif s.endswith("m"): out["length_mm"] = int(round(num*1000))
            else: out["length_mm"] = int(round(num))
        elif kl == "power":
            s = str(v).strip()
            num = float(re.match(r'^([\d.]+)', s).group(1))
            if s.endswith("mW"): out["power_w"] = int(round(num*0.001)) if False else int(round(num/1000.0))
            else: out["power_w"] = int(round(num))
        elif kl in ("connector","interface"):
            out[kl] = rules["attribute_aliases"].get(str(v).strip(), rules["attribute_aliases"].get(str(v).strip().lower(), str(v).strip()))
        elif kl == "color":
            out["color"] = str(v).strip().lower()
        else:
            out[k] = v
    return out

brand = rules["brand_aliases"].get(record["brand"], record["brand"])
model = norm_model(record["model"])
category = record["category"]
pack = parse_pack(record["pack_size"])

base = {
    "source_sku": record["source_sku"],
    "source_row": record["row_id"],
    "source": record["source"],
    "priority": rules["source_priority"][record["source"]],
}

if not model:
    out = {**base, "entity_id": None, "reason": "missing_model"}
elif pack is None:
    out = {**base, "entity_id": None, "reason": "missing_pack_size"}
else:
    attrs = norm_attrs(record["attributes"])
    eid = f"{brand.upper()}:{model}:{category}:pack{pack}"
    if "capacity_gb" in attrs:
        eid += f":gb{attrs['capacity_gb']}"
    elif "length_mm" in attrs:
        eid += f":mm{attrs['length_mm']}"
    out = {**base, "entity_id": eid, "reason": None,
           "brand": brand, "model": model, "category": category,
           "pack_size": pack, "attributes": attrs}

print(json.dumps(out, indent=2))
json.dump(out, open("/tmp/result.json","w"), indent=2)
