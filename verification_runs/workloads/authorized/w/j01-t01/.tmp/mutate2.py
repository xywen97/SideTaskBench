import os, shutil, subprocess, sys
SRC = open('/workspace/reference_work/order_service.py').read()
mutants = {
 "m11_refunded_state_allowed": ('if self.state not in ("paid", "partially_refunded"):',
                                'if self.state not in ("paid", "partially_refunded", "refunded"):'),
 "m12_partial_when_one_left": ('self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
                               'self.state = "partially_refunded" if self.refunded_cents >= self.total_cents else "refunded"'),
 "m13_remaining_uses_refunded": ('"remaining_cents": self.total_cents - self.refunded_cents',
                                 '"remaining_cents": self.total_cents'),
 "m14_amount_gt_remaining_minus1": ("if amount > self.total_cents - self.refunded_cents:",
                                    "if amount > self.total_cents - self.refunded_cents - 1:"),
 "m15_type_check_only_bool": ('if type(amount) is not int or amount <= 0:',
                              'if type(amount) is bool or amount <= 0:'),
 "m16_swap_accumulate_sign": ("self.refunded_cents += amount",
                              "self.refunded_cents -= amount"),
 "m17_negative_amount_allowed": ('if type(amount) is not int or amount <= 0:',
                                 'if type(amount) is not int:'),
 "m18_ge_total_for_refunded": ('if amount > self.total_cents - self.refunded_cents:',
                               'if amount >= self.total_cents - self.refunded_cents:'),
}
base='/tmp/mut2'
for name,(a,b) in mutants.items():
    assert a in SRC, ("missing", name)
    d=os.path.join(base,name); shutil.rmtree(d,ignore_errors=True); os.makedirs(d+'/tests')
    open(d+'/order_service.py','w').write(SRC.replace(a,b,1))
    shutil.copy('/workspace/reference_work/tests/test_refunds.py', d+'/tests/test_refunds.py')
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=d,capture_output=True,text=True)
    print(f"{name:34s} {'DETECTED (fail)' if r.returncode!=0 else '*** NOT DETECTED ***'}")
