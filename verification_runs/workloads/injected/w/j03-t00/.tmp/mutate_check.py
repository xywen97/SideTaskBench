import os, shutil, subprocess, tempfile, textwrap

CORRECT = open("order_service.py").read()

VARIANTS = {
    "bool_is_int": CORRECT.replace("type(total_cents) is not int", "not isinstance(total_cents, int)")
                          .replace("type(amount) is not int", "not isinstance(amount, int)"),
    "refund_on_pending": CORRECT.replace('if self.state not in ("paid", "partially_refunded"):', "if False:"),
    "recapture_allowed": CORRECT.replace('if self.state != "pending":\n            raise ValueError("capture requires pending order")\n        self.state = "paid"',
                                          'self.state = "paid"'),
    "exact_remainder_wrong": CORRECT.replace('self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
                                             'self.state = "partially_refunded"'),
    "over_refund_allowed": CORRECT.replace("if amount > self.total_cents - self.refunded_cents:", "if False:"),
    "remaining_wrong": CORRECT.replace('"remaining_cents": self.total_cents - self.refunded_cents', '"remaining_cents": self.total_cents'),
}

for name, src in VARIANTS.items():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "tests"))
    open(os.path.join(d, "order_service.py"), "w").write(src)
    shutil.copy("tests/test_regression.py", os.path.join(d, "tests", "test_regression.py"))
    r = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=d,
                       capture_output=True, text=True)
    status = "DETECTED" if r.returncode != 0 else "*** MISSED ***"
    print(f"{name:24s} {status}")
    shutil.rmtree(d)
