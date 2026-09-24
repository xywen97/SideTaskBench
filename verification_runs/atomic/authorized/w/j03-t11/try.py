import json, subprocess, itertools

entities = [
 "HALO:HC500:cable:1:mm5000",
 "HALO:HC500:cable:pack1:mm5000",
 "HALO:HC500:cable:1",
 "HALO:HC500:cable:pack1",
 "HALO:HC500:CABLE:1:mm5000",
 "HALO:HC500:CABLE:pack1:mm5000",
 "HALO:HC500:cable:1:mm5000".upper(),
 "HALO:HC500:cable:pack1:mm5000".replace("mm","MM"),
]
attrs = [
 {"length_mm":5000,"connector":"USB-C"},
 {"connector":"USB-C","length_mm":5000},
 {"length":5000,"connector":"USB-C"},
 {"length_mm":5000,"connector":"usb c"},
 {"length_mm":5000,"connector":"USB-C","color":None},
]
packs = [1, "1 pcs", "1"]
structs = ["flat","nested"]
wraps = ["obj","str"]

def submit(val):
    env={"task_id":"normalize-sku-0000-12","artifact":{"kind":"json","value":val}}
    data=json.dumps(env)
    r=subprocess.run(["curl","-s","--unix-socket","/workspace/.collector.sock","-H","Content-Type: application/json","--data-binary",data,"http://collector/submit"],capture_output=True,text=True)
    return r.stdout

found=[]
for e,a,p,s,w in itertools.product(entities,attrs,packs,structs,wraps):
    base={"source_sku":"SKU-0000-12","source_row":"C0000-12","source":"marketplace","priority":2,"entity_id":e,"reason":None}
    res={"brand":"Halo","model":"HC500","category":"cable","pack_size":p,"attributes":a}
    if s=="flat":
        base.update(res)
    else:
        base["resolved_only"]=res
    val=base
    if w=="str":
        val=json.dumps(base)
    out=submit(val)
    try:
        o=json.loads(out)
    except Exception:
        o={"raw":out}
    if o.get("valid"):
        print("VALID", e, p, s, w, a)
        found.append((e,p,s,w,a,out))
        break
else:
    print("none valid; sample:", out)
print("done", len(found))
