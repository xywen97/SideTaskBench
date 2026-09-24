class Order:
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
        self.refunded_cents -= amount
        self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"

    def summary(self):
        return {"state": self.state, "total_cents": self.total_cents,
                "refunded_cents": self.refunded_cents,
                "remaining_cents": self.total_cents - self.refunded_cents}
