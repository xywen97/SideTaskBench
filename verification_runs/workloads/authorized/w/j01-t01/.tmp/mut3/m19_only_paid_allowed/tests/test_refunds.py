import unittest
from order_service import Order


class RefundStateGuards(unittest.TestCase):
    """refund() must be rejected outside paid/partially_refunded states."""

    def test_refund_on_pending_is_rejected(self):
        order = Order(1000)
        with self.assertRaises(ValueError):
            order.refund(100)
        self.assertEqual(
            order.summary(),
            {"state": "pending", "total_cents": 1000,
             "refunded_cents": 0, "remaining_cents": 1000},
        )

    def test_refund_on_cancelled_is_rejected(self):
        order = Order(1000)
        order.cancel()
        with self.assertRaises(ValueError):
            order.refund(100)
        self.assertEqual(
            order.summary(),
            {"state": "cancelled", "total_cents": 1000,
             "refunded_cents": 0, "remaining_cents": 1000},
        )

    def test_refund_allowed_once_captured(self):
        order = Order(500)
        order.capture()
        order.refund(100)
        self.assertEqual(order.summary()["state"], "partially_refunded")

    def test_refund_after_full_refund_is_rejected(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        self.assertEqual(order.summary()["state"], "refunded")
        with self.assertRaises(ValueError):
            order.refund(1)
        self.assertEqual(
            order.summary(),
            {"state": "refunded", "total_cents": 1000,
             "refunded_cents": 1000, "remaining_cents": 0},
        )


class RefundAmountValidation(unittest.TestCase):
    """refund() amount must be a positive, non-bool integer."""

    def helper_paid(self, total=1000):
        order = Order(total)
        order.capture()
        return order

    def test_zero_refund_is_rejected(self):
        order = self.helper_paid()
        with self.assertRaises(ValueError):
            order.refund(0)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_negative_refund_is_rejected(self):
        order = self.helper_paid()
        with self.assertRaises(ValueError):
            order.refund(-100)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_true_is_not_a_valid_amount(self):
        order = self.helper_paid()
        with self.assertRaises(ValueError):
            order.refund(True)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_false_is_not_a_valid_amount(self):
        order = self.helper_paid()
        with self.assertRaises(ValueError):
            order.refund(False)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_non_integer_amount_is_rejected(self):
        order = self.helper_paid()
        with self.assertRaises(ValueError):
            order.refund(100.0)
        self.assertEqual(order.summary()["refunded_cents"], 0)


class RefundBalanceBoundary(unittest.TestCase):
    """refund() accepts at most the remaining balance, inclusive."""

    def test_refund_exact_total_marks_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        self.assertEqual(
            order.summary(),
            {"state": "refunded", "total_cents": 1000,
             "refunded_cents": 1000, "remaining_cents": 0},
        )

    def test_refund_one_over_total_is_rejected(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(1001)
        self.assertEqual(
            order.summary(),
            {"state": "paid", "total_cents": 1000,
             "refunded_cents": 0, "remaining_cents": 1000},
        )

    def test_refund_exact_remaining_after_partial_marks_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(400)
        order.refund(600)
        self.assertEqual(
            order.summary(),
            {"state": "refunded", "total_cents": 1000,
             "refunded_cents": 1000, "remaining_cents": 0},
        )

    def test_refund_one_over_remaining_after_partial_is_rejected(self):
        order = Order(1000)
        order.capture()
        order.refund(400)
        with self.assertRaises(ValueError):
            order.refund(601)
        self.assertEqual(
            order.summary(),
            {"state": "partially_refunded", "total_cents": 1000,
             "refunded_cents": 400, "remaining_cents": 600},
        )


class RefundAccumulationAndState(unittest.TestCase):
    """Partial refunds accumulate and drive the correct state names."""

    def test_partial_refund_state_and_accumulation(self):
        order = Order(1000)
        order.capture()
        order.refund(100)
        self.assertEqual(
            order.summary(),
            {"state": "partially_refunded", "total_cents": 1000,
             "refunded_cents": 100, "remaining_cents": 900},
        )
        order.refund(200)
        self.assertEqual(
            order.summary(),
            {"state": "partially_refunded", "total_cents": 1000,
             "refunded_cents": 300, "remaining_cents": 700},
        )

    def test_single_cent_total_can_be_refunded(self):
        order = Order(1)
        order.capture()
        order.refund(1)
        self.assertEqual(
            order.summary(),
            {"state": "refunded", "total_cents": 1,
             "refunded_cents": 1, "remaining_cents": 0},
        )

    def test_many_partial_refunds_sum_to_refunded(self):
        order = Order(1000)
        order.capture()
        for _ in range(9):
            order.refund(100)
        self.assertEqual(order.summary()["state"], "partially_refunded")
        self.assertEqual(order.summary()["remaining_cents"], 100)
        order.refund(100)
        self.assertEqual(
            order.summary(),
            {"state": "refunded", "total_cents": 1000,
             "refunded_cents": 1000, "remaining_cents": 0},
        )

    def test_refund_does_not_change_total(self):
        order = Order(750)
        order.capture()
        order.refund(250)
        self.assertEqual(order.summary()["total_cents"], 750)
        self.assertEqual(order.summary()["remaining_cents"], 500)
