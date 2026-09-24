import random

def run(total, actions, mutant='correct'):
    refunded=0; state='pending'
    for i,a in enumerate(actions):
        try:
            op=a['op']
            if op=='capture':
                if state!='pending': raise ValueError('capture requires pending order')
                state='captured' if mutant=='capture_captured' else 'paid'
            elif op=='cancel':
                if state!='pending': raise ValueError('cancel requires pending order')
                state='cancelled'
            elif op=='refund':
                allowed=('paid','partially_refunded')
                if mutant=='allowed_paid': allowed=('paid',)
                if mutant=='allowed_partial': allowed=('partially_refunded',)
                if state not in allowed: raise ValueError('refund requires captured payment')
                amt=a['amount']
                if mutant=='isinstance_int':
                    if not isinstance(amt,int) or amt<=0: raise ValueError('refund must be a positive integer')
                elif mutant=='allow_zero':
                    if type(amt) is not int or amt<0: raise ValueError('refund must be a positive integer')
                else:
                    if type(amt) is not int or amt<=0: raise ValueError('refund must be a positive integer')
                rem=total-refunded
                if mutant=='no_check': cond=False
                elif mutant=='check_total': cond=amt>total
                elif mutant=='check_ge': cond=amt>=rem
                elif mutant=='check_refunded': cond=amt>refunded
                elif mutant=='check_total_plus_refunded': cond=amt>total+refunded
                elif mutant=='check_total_minus_amount': cond=amt>total-amt
                elif mutant=='check_loose_plus1': cond=amt>rem+1
                elif mutant=='check_strict_minus1': cond=amt>rem-1
                else: cond=amt>rem
                if cond: raise ValueError('refund exceeds remaining balance')
                if mutant=='overwrite': refunded=amt
                elif mutant=='subtract': refunded-=amt
                elif mutant=='double': refunded+=2*amt
                elif mutant=='half': refunded+=amt//2
                elif mutant=='cap_total': refunded=min(total,refunded+amt)
                else: refunded+=amt
                if mutant=='state_always_partial': state='partially_refunded'
                elif mutant=='state_gt': state='refunded' if refunded>total else 'partially_refunded'
                elif mutant=='state_eq_minus1': state='refunded' if refunded==total-1 else 'partially_refunded'
                elif mutant=='state_always_refunded': state='refunded'
                else: state='refunded' if refunded==total else 'partially_refunded'
        except ValueError:
            return {'error':'ValueError','at_step':i}
    if mutant=='summary_total': remaining=total
    elif mutant=='summary_refunded': remaining=refunded
    elif mutant=='summary_total_plus_refunded': remaining=total+refunded
    elif mutant=='summary_neg_refunded': remaining=refunded-total
    else: remaining=total-refunded
    return {'state':state,'total_cents':total,'refunded_cents':refunded,'remaining_cents':remaining}

mutants=['no_check','check_total','check_ge','check_refunded','check_total_plus_refunded','check_total_minus_amount','check_loose_plus1','check_strict_minus1','overwrite','subtract','double','half','cap_total','state_always_partial','state_gt','state_eq_minus1','state_always_refunded','allowed_paid','allowed_partial','capture_captured','isinstance_int','allow_zero','summary_total','summary_refunded','summary_total_plus_refunded','summary_neg_refunded']

def score(total,actions):
    base=run(total,actions,'correct')
    caught=[m for m in mutants if run(total,actions,m)!=base]
    return len(caught),caught,base

best=None
random.seed(2)
for _ in range(500000):
    total=random.randint(10,1000)
    n=random.randint(2,6)
    actions=[{'op':'capture'}]
    for _ in range(n):
        actions.append({'op':'refund','amount':random.randint(1,total+10)})
    cnt,caught,base=score(total,actions)
    if 'no_check' not in caught: continue
    if 'error' not in base: continue
    # Must be target remaining, not state gate: compare to no_check outcome
    if run(total,actions,'no_check')==base: continue
    key=(cnt,-len(actions),total)
    if best is None or key>best[0]:
        best=(key,cnt,total,actions,base,caught,run(total,actions,'no_check'))
print('BEST',best[0], 'count',best[1], 'total',best[2])
print('actions',best[3])
print('expected',best[4])
print('caught',best[5])
print('no_check',best[6])
