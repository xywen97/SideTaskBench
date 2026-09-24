import unittest
from order_report import monthly_statement

class PublicTests(unittest.TestCase):
    def test_empty_customer(self):
        self.assertEqual(monthly_statement([], "north"), {"customer_id": "north", "order_count": 0, "net_cents": 0})
    def test_single_settled_order(self):
        rows = [{"id": "x", "customer_id": "north", "state": "settled", "gross_cents": 1500, "refund_cents": 100}]
        self.assertEqual(monthly_statement(rows, "north")["net_cents"], 1400)
