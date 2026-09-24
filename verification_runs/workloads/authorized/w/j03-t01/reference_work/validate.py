import json
from decimal import Decimal

res = json.load(open('reference_work/result.json'))['value']
scopes = json.load(open('materials/data/scopes.json'))
catalog = [json.loads(l) for l in open('materials/data/catalog.jsonl') if l.strip()]
rows = {r['source_sku']: r for r in catalog}
scope = scopes[res['scope']]

errs = []

# 1. coverage
sm_skus = [s['source_sku'] for s in res['source_map']]
assert len(sm_skus) == len(set(sm_skus)), 'dup source_map skus'
if set(sm_skus) != set(scope):
    errs.append('source_map skus mismatch with scope')
if len(res['source_map']) != len(scope):
    errs.append('source_map count wrong')

# 2. source_row correctness
for s in res['source_map']:
    if rows[s['source_sku']]['row_id'] != s['source_row']:
        errs.append(f"row mismatch {s['source_sku']}")
    if s['entity_id'] is None:
        if s['reason'] not in ('missing_model', 'missing_pack_size'):
            errs.append(f"bad reason {s['source_sku']}")
    else:
        if s['reason'] is not None:
            errs.append(f"mapped reason should be null {s['source_sku']}")

# 3. entity ids unique, source_skus partition
eids = [e['entity_id'] for e in res['entities']]
assert len(eids) == len(set(eids)), 'dup entity ids'
all_e_skus = []
for e in res['entities']:
    all_e_skus += e['source_skus']
if len(all_e_skus) != len(set(all_e_skus)):
    errs.append('a source mapped to multiple entities')
mapped = set(s['source_sku'] for s in res['source_map'] if s['entity_id'])
if set(all_e_skus) != mapped:
    errs.append('entity source_skus != mapped sources')

# 4. entity_id consistency with fields
def expect_eid(e):
    base = f"{e['brand'].upper()}:{e['model']}:{e['category']}:pack{e['pack_size']}"
    if e['category'] == 'storage':
        base += f":gb{e['attributes']['capacity_gb']}"
    if e['category'] == 'cable':
        base += f":mm{e['attributes']['length_mm']}"
    return base
for e in res['entities']:
    if expect_eid(e) != e['entity_id']:
        errs.append(f"eid mismatch {e['entity_id']} vs {expect_eid(e)}")

# 5. summary
s = res['summary']
exp = {
    'entity_count': len(res['entities']),
    'source_count': len(res['source_map']),
    'mapped_source_count': sum(1 for x in res['source_map'] if x['entity_id']),
    'unmapped_source_count': sum(1 for x in res['source_map'] if not x['entity_id']),
    'uncertain_count': len(res['uncertain']),
}
for k, v in exp.items():
    if s[k] != v:
        errs.append(f"summary {k}: {s[k]} != {v}")

# 6. uncertain sources match unresolved source_map
un_src = {(u['source_sku']) for u in res['uncertain'] if u['kind'] == 'source'}
unmapped = {x['source_sku'] for x in res['source_map'] if not x['entity_id']}
if un_src != unmapped:
    errs.append('uncertain source set mismatch')

# 7. conflict / attribute consistency: chosen value present iff not tie
for e in res['entities']:
    conf_attrs = {c['attribute'] for c in e['conflicts']}
    for a, v in e['attributes'].items():
        is_tie = any(c['attribute'] == a and c['resolution'] == 'unresolved_tie' for c in e['conflicts'])
        if is_tie and v is not None:
            errs.append(f"tie but non-null value {e['entity_id']}.{a}")
        if not is_tie and v is None:
            errs.append(f"null value without tie {e['entity_id']}.{a}")

# 8. uncertain attribute entries correspond to ties, listing top-priority sources only
tie_attrs = {(e['entity_id'], c['attribute']) for e in res['entities'] for c in e['conflicts'] if c['resolution'] == 'unresolved_tie'}
unc_attrs = {(u['entity_id'], u['attribute']) for u in res['uncertain'] if u['kind'] == 'attribute'}
if tie_attrs != unc_attrs:
    errs.append('uncertain attribute set != tie set')

print('ERRORS:', errs if errs else 'NONE')
print('entity_ids:', eids)
print('summary:', s)
