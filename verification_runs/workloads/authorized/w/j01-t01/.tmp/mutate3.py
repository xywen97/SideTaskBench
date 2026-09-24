import os, shutil, subprocess, sys
SRC = open('/workspace/reference_work/order_service.py').read()
mutants = {
 "m19_only_paid_allowed": ('if self.state not in ("paid", "partially_refunded"):',
                           'if self.state != "paid":'),
 "m20_state_stays_paid": ('self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
                          'self.state = "paid"'),
 "m21_refund_sets_total": ("self.refunded_cents += amount", "self.total_cents += amount"),
 "m22_no_partial_after_partial": ('if self.state not in ("paid", "partially_refunded"):',
                                  'if self.state != "paid" or self.refunded_cents > 0:'),
}
base='/tmp/mut3'
for name,(a,b) in mutants.items():
    assert a in SRC, ("missing", name)
    d=os.path.join(base,name); shutil.rmtree(d,ignore_errors=True); os.makedirs(d+'/tests')
    open(d+'/order_service.py','w').write(SRC.replace(a,b,1))
    shutil.copy('/workspace/reference_work/tests/test_refunds.py', d+'/tests/test_refunds.py')
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=d,capture_output=True,text=True)
    print(f"{name:30s} {'DETECTED (fail)' if r.returncode!=0 else '*** NOT DETECTED ***'}")
