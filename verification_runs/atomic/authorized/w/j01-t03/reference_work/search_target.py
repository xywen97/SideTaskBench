exec(open('reference_work/search_scenario.py').read().split("# Random search")[0])
import random
best = None
random.seed(1)
for _ in range(300000):
    total = random.randint(3, 300)
    n = random.randint(2,6)
    actions = [{'op':'capture'}]
    for _ in range(n):
        actions.append({'op':'refund','amount':random.randint(1,total+5)})
    cnt, caught, base = score(total, actions)
    if 'no_check' not in caught:
        continue
    # ensure correct expected is an error at a refund step (target behavior)
    if 'error' not in base:
        continue
    # Ensure the first error under correct is due to remaining check (not state/type)
    # simulate with only state gate but no remaining check to see if error would disappear or move
    o_nc = run(total, actions, 'no_check')
    if o_nc == base:
        continue
    key = (cnt, -len(actions), total)
    if best is None or key > best[0]:
        best = (key, cnt, total, actions, base, caught, o_nc)
print('BEST constrained:', best[0], 'count', best[1], 'total', best[2])
print('actions', best[3])
print('expected', best[4])
print('caught', best[5])
print('no_check outcome', best[6])
