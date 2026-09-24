class Ledger:
    def __init__(self, rows):
        self.rows = rows

    def orders(self, customer_id):
        return [{"id": row["id"], "amount": "%.2f" % ((row["gross_cents"] - row["refund_cents"]) / 100)}
                for row in self.rows if row["customer_id"] == customer_id and row["state"] == "settled"]
