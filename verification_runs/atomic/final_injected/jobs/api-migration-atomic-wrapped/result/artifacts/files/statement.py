from normalize_order import normalize_order
from collect_orders import collect_orders
from customer_totals import customer_totals


def statement(pages, start_token, customer_id):
    return customer_totals([normalize_order(row) for row in collect_orders(pages, start_token)], customer_id)
