import unittest

from order_service import Order


class OrderConstructorTests(unittest.TestCase):
    def test_accepts_positive_integer(self):
        order = Order(1000)
        self.assertEqual(order.total_cents, 1000)
        self.assertEqual(order.refunded_cents, 0)

    def test_accepts_minimal_amount(self):
        self.assertEqual(Order(1).total_cents, 1)

    def test_rejects_zero_and_negative(self):
        for bad in (0, -1, -1000):
            with self.assertRaises(ValueError):
                Order(bad)

    def test_rejects_bool(self):
        with self.assertRaises(ValueError):
            Order(True)

    def test_rejects_non_integer(self):
        for bad in (10.0, "1000", None, [1000]):
            with self.assertRaises(ValueError):
                Order(bad)


class OrderCaptureTests(unittest.TestCase):
    def test_capture_moves_pending_to_paid(self):
        order = Order(1000)
        order.capture()
        self.assertEqual(order.state, "paid")
        self.assertEqual(order.summary()["state"], "paid")

    def test_repeated_capture_raises(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.state, "paid")

    def test_capture_after_cancel_raises(self):
        order = Order(1000)
        order.cancel()
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.state, "cancelled")

    def test_capture_after_refund_raises(self):
        order = Order(1000)
        order.capture()
        order.refund(400)
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.state, "partially_refunded")


class OrderCancelTests(unittest.TestCase):
    def test_cancel_moves_pending_to_cancelled(self):
        order = Order(1000)
        order.cancel()
        self.assertEqual(order.state, "cancelled")
        self.assertEqual(order.summary()["state"], "cancelled")

    def test_cancel_after_capture_raises(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.state, "paid")

    def test_cancel_after_partial_refund_raises(self):
        order = Order(1000)
        order.capture()
        order.refund(100)
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.state, "partially_refunded")

    def test_cancel_after_full_refund_raises(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.state, "refunded")

    def test_repeated_cancel_raises(self):
        order = Order(1000)
        order.cancel()
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.state, "cancelled")


class OrderRefundTests(unittest.TestCase):
    def test_refund_on_pending_raises(self):
        order = Order(1000)
        with self.assertRaises(ValueError):
            order.refund(100)

    def test_refund_on_cancelled_raises(self):
        order = Order(1000)
        order.cancel()
        with self.assertRaises(ValueError):
            order.refund(100)

    def test_partial_refund_sets_partially_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(400)
        self.assertEqual(order.summary(), {
            "state": "partially_refunded",
            "total_cents": 1000,
            "refunded_cents": 400,
            "remaining_cents": 600,
        })

    def test_full_refund_sets_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        self.assertEqual(order.summary(), {
            "state": "refunded",
            "total_cents": 1000,
            "refunded_cents": 1000,
            "remaining_cents": 0,
        })

    def test_refund_exact_total_in_one_step(self):
        order = Order(1)
        order.capture()
        order.refund(1)
        self.assertEqual(order.state, "refunded")

    def test_refunds_accumulate(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        order.refund(200)
        self.assertEqual(order.summary(), {
            "state": "partially_refunded",
            "total_cents": 1000,
            "refunded_cents": 500,
            "remaining_cents": 500,
        })

    def test_exact_remainder_becomes_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        order.refund(700)
        self.assertEqual(order.summary(), {
            "state": "refunded",
            "total_cents": 1000,
            "refunded_cents": 1000,
            "remaining_cents": 0,
        })

    def test_exceeding_remaining_raises_and_preserves_state(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        with self.assertRaises(ValueError):
            order.refund(701)
        self.assertEqual(order.refunded_cents, 300)
        self.assertEqual(order.state, "partially_refunded")

    def test_refund_more_than_total_raises(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(1001)

    def test_refund_zero_or_negative_raises(self):
        order = Order(1000)
        order.capture()
        for bad in (0, -1, -500):
            with self.assertRaises(ValueError):
                order.refund(bad)
        self.assertEqual(order.refunded_cents, 0)

    def test_refund_bool_raises(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(True)
        with self.assertRaises(ValueError):
            order.refund(False)
        self.assertEqual(order.refunded_cents, 0)

    def test_refund_non_integer_raises(self):
        order = Order(1000)
        order.capture()
        for bad in (100.0, "100"):
            with self.assertRaises(ValueError):
                order.refund(bad)

    def test_refund_after_full_refund_raises(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        with self.assertRaises(ValueError):
            order.refund(1)
        self.assertEqual(order.state, "refunded")


class OrderSummaryTests(unittest.TestCase):
    def test_initial_summary(self):
        self.assertEqual(Order(1000).summary(), {
            "state": "pending",
            "total_cents": 1000,
            "refunded_cents": 0,
            "remaining_cents": 1000,
        })

    def test_summary_tracks_remaining(self):
        order = Order(2500)
        order.capture()
        order.refund(500)
        self.assertEqual(order.summary()["remaining_cents"], 2000)
