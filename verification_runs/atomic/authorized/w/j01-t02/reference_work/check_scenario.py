from copy import deepcopy

CORRECT_SOURCE = '''class Order:
    def __init__(self, total_cents):
        if type(total_cents) is not int or total_cents <= 0:
            raise ValueError("total must be a positive integer")
        self.total_cents = total_cents
        self.refunded_cents = 0
        self.state = "pending"

    def capture(self):
        if self.state != "pending":
            raise ValueError("capture requires pending order")
        self.state = "paid"

    def cancel(self):
        if self.state != "pending":
            raise ValueError("cancel requires pending order")
        self.state = "cancelled"

    def refund(self, amount):
        if self.state not in ("paid", "partially_refunded"):
            raise ValueError("refund requires captured payment")
        if type(amount) is not int or amount <= 0:
            raise ValueError("refund must be a positive integer")
        if amount > self.total_cents - self.refunded_cents:
            raise ValueError("refund exceeds remaining balance")
        self.refunded_cents += amount
        self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"

    def summary(self):
        return {"state": self.state, "total_cents": self.total_cents,
                "refunded_cents": self.refunded_cents,
                "remaining_cents": self.total_cents - self.refunded_cents}
'''

FAULTY_ZERO_ALLOWED = CORRECT_SOURCE.replace('if type(amount) is not int or amount <= 0:', 'if type(amount) is not int or amount < 0:')

SCENARIO = {
    "total_cents": 100,
    "actions": [
        {"op": "capture"},
        {"op": "refund", "amount": 0},
    ],
    "expected": {"error": "ValueError", "at_step": 1},
}

def run(source, scenario):
    ns = {}
    exec(source, ns)
    Order = ns['Order']
    order = Order(scenario['total_cents'])
    for i, action in enumerate(scenario['actions']):
        op = action['op']
        try:
            if op == 'capture':
                order.capture()
            elif op == 'cancel':
                order.cancel()
            elif op == 'refund':
                order.refund(action['amount'])
            else:
                raise AssertionError('unknown op')
        except ValueError:
            return {"error": "ValueError", "at_step": i}
    return order.summary()

for name, source in [('correct', CORRECT_SOURCE), ('faulty-zero-allowed', FAULTY_ZERO_ALLOWED)]:
    result = run(source, SCENARIO)
    print(name, result)
    if name == 'correct':
        assert result == SCENARIO['expected'], (result, SCENARIO['expected'])
    else:
        assert result != SCENARIO['expected'], "fault not exposed"
print('scenario validates against correct implementation and exposes zero-refund fault')
