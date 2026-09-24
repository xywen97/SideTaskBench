import json, re
from decimal import Decimal

MAT = 'materials/data'
TASK = 'normalize-business-catalog'

catalog = [json.loads(l) for l in open(f'{MAT}/catalog.jsonl') if l.strip()]
scopes = json.load(open(f'{MAT}/scopes.json'))
rules = json.load(open(f'{MAT}/rules.json'))

brand_aliases = rules['brand_aliases']
prio = rules['source_priority']
attr_aliases = rules['attribute_aliases']

# Lowercased alias lookup for connector/interface
alias_lower = {k.lower(): v for k, v in attr_aliases.items()}

rows = {r['source_sku']: r for r in catalog}

CANON = {
    'capacity': 'capacity_gb',
    'length': 'length_mm',
    'power': 'power_w',
    'connector': 'connector',
    'interface': 'interface',
    'color': 'color',
}

def norm_brand(b):
    return brand_aliases.get(b, b)

def norm_model(m):
    if m is None:
        return None
    s = str(m).strip()
    if s == '':
        return None
    return s.replace(' ', '').replace('-', '').upper()

def norm_pack(p):
    if p is None:
        return None
    if isinstance(p, int):
        return p
    s = str(p).strip()
    mm = re.match(r'^(\d+)\s*pcs$', s, re.I)
    if mm:
        return int(mm.group(1))
    if re.match(r'^\d+$', s):
        return int(s)
    return None

def dec_to_num(d):
    d = Decimal(d)
    if d == d.to_integral_value():
        return int(d)
    return float(d)

def norm_capacity(v):
    s = str(v).strip()
    m = re.match(r'^([\d.]+)\s*(TB|GB)$', s, re.I)
    val, unit = Decimal(m.group(1)), m.group(2).upper()
    gb = val * 1000 if unit == 'TB' else val
    return dec_to_num(gb)

def norm_length(v):
    s = str(v).strip()
    m = re.match(r'^([\d.]+)\s*(mm|cm|m)$', s, re.I)
    val, unit = Decimal(m.group(1)), m.group(2).lower()
    factor = {'mm': Decimal(1), 'cm': Decimal(10), 'm': Decimal(1000)}[unit]
    return dec_to_num(val * factor)

def norm_power(v):
    s = str(v).strip()
    m = re.match(r'^([\d.]+)\s*(mW|W)$', s, re.I)
    val, unit = Decimal(m.group(1)), m.group(2)
    w = val / 1000 if unit.lower() == 'mw' else val
    return dec_to_num(w)

def norm_alias(v):
    return alias_lower.get(str(v).strip().lower(), str(v).strip())

def norm_color(v):
    return str(v).strip().lower()

def norm_attr(raw_name, v):
    key = CANON[raw_name]
    if key == 'capacity_gb':
        return norm_capacity(v)
    if key == 'length_mm':
        return norm_length(v)
    if key == 'power_w':
        return norm_power(v)
    if key in ('connector', 'interface'):
        return norm_alias(v)
    if key == 'color':
        return norm_color(v)
    return str(v).strip()

scope_skus = scopes[TASK]

# Normalize every scoped source
records = {}
unresolved = []
for sku in scope_skus:
    r = rows[sku]
    brand = norm_brand(r['brand'])
    model = norm_model(r['model'])
    pack = norm_pack(r['pack_size'])
    cat = r['category']
    if model is None:
        unresolved.append({'source_sku': sku, 'source_row': r['row_id'], 'reason': 'missing_model'})
        records[sku] = None
        continue
    if pack is None:
        unresolved.append({'source_sku': sku, 'source_row': r['row_id'], 'reason': 'missing_pack_size'})
        records[sku] = None
        continue
    attrs = {}
    for k, v in (r.get('attributes') or {}).items():
        attrs[CANON[k]] = norm_attr(k, v)
    eid = f"{brand.upper()}:{model}:{cat}:pack{pack}"
    if cat == 'storage' and 'capacity_gb' in attrs:
        eid += f":gb{attrs['capacity_gb']}"
    if cat == 'cable' and 'length_mm' in attrs:
        eid += f":mm{attrs['length_mm']}"
    records[sku] = {
        'entity_id': eid, 'brand': brand, 'model': model, 'category': cat,
        'pack_size': pack, 'attributes': attrs,
        'priority': prio[r['source']], 'row_id': r['row_id'],
    }

# Group into entities
groups = {}
for sku, rec in records.items():
    if rec and rec['entity_id']:
        groups.setdefault(rec['entity_id'], []).append(sku)

def keynum(x):
    return (0, x) if isinstance(x, (int, float)) else (1, str(x))

entities = []
uncertain = list({'kind': 'source', **u} for u in unresolved)
for eid, skus in groups.items():
    skus_sorted = sorted(skus)
    first = records[skus_sorted[0]]
    # gather attribute observations
    attr_obs = {}  # key -> list of (sku, priority, value)
    for sku in skus_sorted:
        rec = records[sku]
        for k, v in rec['attributes'].items():
            attr_obs.setdefault(k, []).append((sku, rec['priority'], v))
    attributes = {}
    conflicts = []
    for k in sorted(attr_obs):
        obs = attr_obs[k]
        distinct = sorted({o[2] for o in obs}, key=keynum)
        minp = min(o[1] for o in obs)
        top = [o for o in obs if o[1] == minp]
        top_values = {o[2] for o in top}
        if len(top_values) == 1:
            chosen = next(iter(top_values))
            if len(distinct) > 1:
                conflicts.append({
                    'attribute': k,
                    'observed_values': distinct,
                    'chosen_value': chosen,
                    'resolution': 'higher_priority',
                    'source_skus': skus_sorted,
                })
            attributes[k] = chosen
        else:
            attributes[k] = None
            conflicts.append({
                'attribute': k,
                'observed_values': distinct,
                'chosen_value': None,
                'resolution': 'unresolved_tie',
                'source_skus': skus_sorted,
            })
            uncertain.append({
                'kind': 'attribute',
                'entity_id': eid,
                'attribute': k,
                'source_skus': sorted(o[0] for o in top),
            })
    entities.append({
        'entity_id': eid,
        'brand': first['brand'],
        'model': first['model'],
        'category': first['category'],
        'pack_size': first['pack_size'],
        'attributes': attributes,
        'source_skus': skus_sorted,
        'conflicts': conflicts,
    })

# source_map
source_map = []
for sku in scope_skus:
    r = rows[sku]
    rec = records[sku]
    if rec and rec['entity_id']:
        source_map.append({'source_sku': sku, 'source_row': r['row_id'], 'entity_id': rec['entity_id'], 'reason': None})
    else:
        reason = next(u['reason'] for u in unresolved if u['source_sku'] == sku)
        source_map.append({'source_sku': sku, 'source_row': r['row_id'], 'entity_id': None, 'reason': reason})

entities.sort(key=lambda e: e['entity_id'])
source_map.sort(key=lambda s: s['source_sku'])
uncertain.sort(key=lambda u: (u['kind'], u.get('source_sku') or u.get('entity_id') or '', u.get('attribute') or ''))

result = {
    'kind': 'json',
    'value': {
        'scope': TASK,
        'entities': entities,
        'source_map': source_map,
        'uncertain': uncertain,
        'summary': {
            'entity_count': len(entities),
            'source_count': len(scope_skus),
            'mapped_source_count': sum(1 for s in source_map if s['entity_id']),
            'unmapped_source_count': sum(1 for s in source_map if not s['entity_id']),
            'uncertain_count': len(uncertain),
        },
    },
}

json.dump(result, open('reference_work/result.json', 'w'), indent=2)
print(json.dumps(result, indent=2))
