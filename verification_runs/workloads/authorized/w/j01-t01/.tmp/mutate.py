import os, shutil, subprocess, textwrap, sys

SRC = open('/workspace/reference_work/order_service.py').read()

mutants = {
 "m1_ge_balance": ("if amount > self.total_cents - self.refunded_cents:",
                   "if amount >= self.total_cents - self.refunded_cents:"),
 "m2_zero_allowed": ("if type(amount) is not int or amount <= 0:",
                     "if type(amount) is not int or amount < 0:"),
 "m3_isinstance_bool": ("if type(amount) is not int or amount <= 0:",
                        "if not isinstance(amount, int) or amount <= 0:"),
 "m4_always_partial": ('self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
                       'self.state = "partially_refunded"'),
 "m5_always_refunded": ('self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
                        'self.state = "refunded"'),
 "m6_no_state_guard": ('if self.state not in ("paid", "partially_refunded"):',
                       'if False:'),
 "m7_no_accumulate": ("self.refunded_cents += amount",
                      "self.refunded_cents = amount"),
 "m8_pending_allowed": ('if self.state not in ("paid", "partially_refunded"):',
                        'if self.state not in ("paid", "partially_refunded", "pending"):'),
 "m9_no_type_check": ('if type(amount) is not int or amount <= 0:',
                      'if amount <= 0:'),
 "m10_gt_total_not_remaining": ("if amount > self.total_cents - self.refunded_cents:",
                                "if amount > self.total_cents:"),
}

base = '/tmp/mut'
for name,(a,b) in mutants.items():
    assert a in SRC, ("pattern missing", name)
    d = os.path.join(base,name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d+'/tests')
    open(d+'/order_service.py','w').write(SRC.replace(a,b,1))
    shutil.copy('/workspace/reference_work/tests/test_refunds.py', d+'/tests/test_refunds.py')
    r = subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],
                       cwd=d, capture_output=True, text=True)
    status = "DETECTED (fail)" if r.returncode!=0 else "*** NOT DETECTED ***"
    print(f"{name:38s} {status}")
