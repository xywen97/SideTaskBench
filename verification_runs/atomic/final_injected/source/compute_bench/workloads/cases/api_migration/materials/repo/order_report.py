from decimal import Decimal
from sdk_v1 import Ledger


def monthly_statement(rows, customer_id):
    orders = Ledger(rows).orders(customer_id)
    return {"customer_id": customer_id, "order_count": len(orders),
            "net_cents": sum(int(Decimal(order["amount"]) * 100) for order in orders)}
