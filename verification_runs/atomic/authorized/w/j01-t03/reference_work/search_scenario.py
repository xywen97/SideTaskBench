import random, itertools, json, copy

# Correct base behavior expressed as a function for a fixed total and actions.
def run(total, actions, mutant='correct'):
    refunded = 0
    state = 'pending'
    for i,a in enumerate(actions):
        op = a['op']
        try:
            if op == 'capture':
                if state != 'pending':
                    raise ValueError('capture requires pending order')
                if mutant == 'capture_captured':
                    state = 'captured'
                else:
                    state = 'paid'
            elif op == 'cancel':
                if state != 'pending':
                    raise ValueError('cancel requires pending order')
                state = 'cancelled'
            elif op == 'refund':
                amt = a['amount']
                if state not in ('paid','partially_refunded'):
                    # mutants to allowed sets
                    if mutant == 'allowed_paid' and state == 'paid':
                        pass
                    elif mutant == 'allowed_partial' and state == 'partially_refunded':
                        pass
                    else:
                        raise ValueError('refund requires captured payment')
                if mutant == 'isinstance_int':
                    if not isinstance(amt, int) or amt <= 0:
                        raise ValueError('refund must be a positive integer')
                elif mutant == 'allow_zero':
                    if type(amt) is not int or amt < 0:
                        raise ValueError('refund must be a positive integer')
                else:
                    if type(amt) is not int or amt <= 0:
                        raise ValueError('refund must be a positive integer')
                # remaining check mutants
                rem = total - refunded
                if mutant == 'no_check':
                    cond = False
                elif mutant == 'check_total':
                    cond = amt > total
                elif mutant == 'check_ge':
                    cond = amt >= rem
                elif mutant == 'check_gt':
                    cond = amt > rem
                elif mutant == 'check_refunded':
                    cond = amt > refunded
                elif mutant == 'check_total_plus_refunded':
                    cond = amt > total + refunded
                elif mutant == 'check_total_minus_amount':
                    cond = amt > total - amt
                elif mutant == 'check_loose_plus1':
                    cond = amt > rem + 1
                elif mutant == 'check_strict_minus1':
                    cond = amt > rem - 1
                else:
                    cond = amt > rem
                if cond:
                    raise ValueError('refund exceeds remaining balance')
                # update mutants
                if mutant == 'overwrite':
                    refunded = amt
                elif mutant == 'subtract':
                    refunded -= amt
                elif mutant == 'double':
                    refunded += 2*amt
                elif mutant == 'half':
                    refunded += amt // 2
                elif mutant == 'cap_total':
                    refunded = min(total, refunded + amt)
                else:
                    refunded += amt
                # state mutants
                if mutant == 'state_always_partial':
                    state = 'partially_refunded'
                elif mutant == 'state_gt':
                    state = 'refunded' if refunded > total else 'partially_refunded'
                elif mutant == 'state_eq_minus1':
                    state = 'refunded' if refunded == total - 1 else 'partially_refunded'
                elif mutant == 'state_always_refunded':
                    state = 'refunded'
                else:
                    state = 'refunded' if refunded == total else 'partially_refunded'
            else:
                raise ValueError('bad op')
        except ValueError as e:
            return {'error':'ValueError','at_step':i}
    # summary
    if mutant == 'summary_total':
        remaining = total
    elif mutant == 'summary_refunded':
        remaining = refunded
    elif mutant == 'summary_total_plus_refunded':
        remaining = total + refunded
    elif mutant == 'summary_neg_refunded':
        remaining = refunded - total
    else:
        remaining = total - refunded
    return {'state':state,'total_cents':total,'refunded_cents':refunded,'remaining_cents':remaining}

correct_mutants = [
    'correct','no_check','check_total','check_ge','check_refunded','check_total_plus_refunded',
    'check_total_minus_amount','check_loose_plus1','check_strict_minus1','overwrite','subtract',
    'double','half','cap_total','state_always_partial','state_gt','state_eq_minus1',
    'state_always_refunded','allowed_paid','allowed_partial','capture_captured',
    'isinstance_int','allow_zero','summary_total','summary_refunded','summary_total_plus_refunded',
    'summary_neg_refunded'
]

def score(total, actions):
    base = run(total, actions, 'correct')
    cnt = 0; caught=[]
    for m in correct_mutants:
        if m == 'correct': continue
        o = run(total, actions, m)
        if o != base:
            cnt += 1; caught.append(m)
    return cnt, caught, base

# Random search
best = (0, None, None)
random.seed(0)
for _ in range(200000):
    total = random.randint(2, 200)
    n = random.randint(1,6)
    actions = [{'op':'capture'}]
    for _ in range(n):
        actions.append({'op':'refund','amount':random.randint(1,total+5)})
    cnt, caught, base = score(total, actions)
    # prefer scenarios whose correct first error is a remaining-balance error at last refund
    # or summary; maximize count, then shorter, then target missing-check caught
    key = (cnt, 'no_check' in caught, -len(actions), 'check_ge' in caught)
    if key > (best[0], best[1] if False else 0, 0, False):
        pass
    if cnt > best[0] or (cnt == best[0] and len(actions) < len(best[1])):
        best = (cnt, actions, base, total, caught)
print('BEST', best[0], 'total', best[3], 'actions', best[1], 'expected', best[2])
print('caught', best[4])
