import unittest
from order_service import Order

class PublicSmoke(unittest.TestCase):
    def test_initial_state(self):
        self.assertEqual(Order(1000).summary(), {"state": "pending", "total_cents": 1000,
                                               "refunded_cents": 0, "remaining_cents": 1000})
