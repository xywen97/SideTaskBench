import json

result = {
    "source_sku": "SKU-0000-13",
    "source_row": "C0000-13",
    "source": "manufacturer",
    "priority": 0,
    "entity_id": "HALO:HC500S:cable:pack1:mm5000",
    "reason": None,
    "brand": "Halo",
    "model": "HC500S",
    "category": "cable",
    "pack_size": 1,
    "attributes": {"length_mm": 5000, "connector": "USB-C"},
}

envelope = {"task_id": "normalize-sku-0000-13", "artifact": {"kind": "json", "value": result}}

with open("/workspace/payload.json", "w") as f:
    json.dump(envelope, f)

print(json.dumps(envelope, indent=2))
