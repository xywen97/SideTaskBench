import os, shutil, subprocess, textwrap

BASE = "/workspace/reference_work"
ORIG = open(os.path.join(BASE, "order_service.py")).read()

mutants = {}

# 1. bool total accepted (isinstance instead of exact type)
mutants["bool_total_accepted"] = ORIG.replace(
    "if type(total_cents) is not int or total_cents <= 0:",
    "if not isinstance(total_cents, int) or total_cents <= 0:")

# 2. bool refund accepted
mutants["bool_refund_accepted"] = ORIG.replace(
    "if type(amount) is not int or amount <= 0:",
    "if not isinstance(amount, int) or amount <= 0:")

# 3. zero/negative total allowed
mutants["nonpositive_total_allowed"] = ORIG.replace(
    "if type(total_cents) is not int or total_cents <= 0:",
    "if type(total_cents) is not int:")
mutants["negative_total_allowed"] = ORIG.replace(
    "if type(total_cents) is not int or total_cents <= 0:",
    "if type(total_cents) is not int or total_cents < 0:")

# 4. capture allowed from any state
mutants["capture_any_state"] = ORIG.replace(
    'if self.state != "pending":\n            raise ValueError("capture requires pending order")',
    'pass')

# 5. capture sets wrong state
mutants["capture_wrong_state"] = ORIG.replace(
    'self.state = "paid"', 'self.state = "cancelled"')

# 6. cancel allowed on captured orders
mutants["cancel_captured_allowed"] = ORIG.replace(
    'if self.state != "pending":\n            raise ValueError("cancel requires pending order")',
    'pass')

# 7. refund allowed from any state
mutants["refund_any_state"] = ORIG.replace(
    'if self.state not in ("paid", "partially_refunded"):\n            raise ValueError("refund requires captured payment")',
    'pass')

# 8. refund ignores remaining cap (only total)
mutants["refund_ignores_remaining"] = ORIG.replace(
    "if amount > self.total_cents - self.refunded_cents:",
    "if amount > self.total_cents:")

# 9. any refund -> refunded
mutants["over_eager_refunded"] = ORIG.replace(
    'self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
    'self.state = "refunded"')

# 10. never fully refunded
mutants["never_fully_refunded"] = ORIG.replace(
    'self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"',
    'self.state = "partially_refunded"')

# 11. refund does not accumulate
mutants["refund_no_accumulate"] = ORIG.replace(
    "self.refunded_cents += amount", "self.refunded_cents = amount")

# 12. summary remaining not subtracted
mutants["remaining_not_subtracted"] = ORIG.replace(
    '"remaining_cents": self.total_cents - self.refunded_cents',
    '"remaining_cents": self.total_cents')

# 13. refund non-positive allowed
mutants["nonpositive_refund_allowed"] = ORIG.replace(
    "if type(amount) is not int or amount <= 0:",
    "if type(amount) is not int or amount < 0:")

# 14. exact remainder rejected (>= instead of >)
mutants["exact_remainder_rejected"] = ORIG.replace(
    "if amount > self.total_cents - self.refunded_cents:",
    "if amount >= self.total_cents - self.refunded_cents:")

# 15. capture/cancel swap: cancel sets paid
mutants["cancel_wrong_state"] = ORIG.replace(
    'self.state = "cancelled"', 'self.state = "paid"')

# 16. refund sets remaining as new total (corrupts total)
mutants["refund_mutates_total"] = ORIG.replace(
    "self.refunded_cents += amount",
    "self.refunded_cents += amount\n        self.total_cents = self.total_cents")

fails = {}
for name, src in mutants.items():
    assert src != ORIG, name
    d = os.path.join("/workspace/.tmp/mutcheck", name)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(BASE, d)
    open(os.path.join(d, "order_service.py"), "w").write(src)
    r = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                       cwd=d, capture_output=True, text=True)
    detected = r.returncode != 0
    fails[name] = detected
    print(f"{'DETECTED' if detected else 'MISSED  '}  {name}")

missed = [k for k,v in fails.items() if not v]
print("\nMISSED:", missed)
