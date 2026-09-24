"""Regression suite for the public Order payment/refund state machine.

The tests exercise only documented public behavior:
    Order(total_cents)  ...
    capture()           pending -> paid, repeats raise ValueError
    cancel()            pending -> cancelled, captured orders cannot cancel
    refund(amount)      paid/partially_refunded only, positive int cents,
                        at most the remaining balance, accumulates, and
                        drives partially_refunded/refunded
    summary()           state, total_cents, refunded_cents, remaining_cents

Only unittest assertions and public Order methods are used.
"""

import unittest

from order_service import Order


class OrderConstructionTests(unittest.TestCase):
    def test_new_order_is_pending_with_full_balance(self):
        self.assertEqual(
            Order(1000).summary(),
            {
                "state": "pending",
                "total_cents": 1000,
                "refunded_cents": 0,
                "remaining_cents": 1000,
            },
        )

    def test_accepts_positive_integer_total(self):
        self.assertEqual(Order(1).summary()["total_cents"], 1)
        self.assertEqual(Order(7).summary()["total_cents"], 7)
        self.assertEqual(Order(2500).summary()["total_cents"], 2500)

    def test_zero_total_is_rejected(self):
        with self.assertRaises(ValueError):
            Order(0)

    def test_negative_total_is_rejected(self):
        with self.assertRaises(ValueError):
            Order(-1)
        with self.assertRaises(ValueError):
            Order(-1000)

    def test_bool_total_is_rejected(self):
        # bool is an int subclass but must not be accepted as an amount.
        with self.assertRaises(ValueError):
            Order(True)
        with self.assertRaises(ValueError):
            Order(False)

    def test_non_integer_total_is_rejected(self):
        for bad in (1.0, 1.5, 100.0, "100", None, [1000]):
            with self.assertRaises(ValueError):
                Order(bad)


class CaptureTests(unittest.TestCase):
    def test_capture_moves_pending_to_paid(self):
        order = Order(500)
        order.capture()
        self.assertEqual(
            order.summary(),
            {
                "state": "paid",
                "total_cents": 500,
                "refunded_cents": 0,
                "remaining_cents": 500,
            },
        )

    def test_repeated_capture_is_rejected(self):
        order = Order(500)
        order.capture()
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.summary()["state"], "paid")
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_capture_after_cancel_is_rejected(self):
        order = Order(500)
        order.cancel()
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.summary()["state"], "cancelled")

    def test_capture_after_partial_refund_is_rejected(self):
        order = Order(500)
        order.capture()
        order.refund(100)
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.summary()["state"], "partially_refunded")

    def test_capture_after_full_refund_is_rejected(self):
        order = Order(500)
        order.capture()
        order.refund(500)
        with self.assertRaises(ValueError):
            order.capture()
        self.assertEqual(order.summary()["state"], "refunded")


class CancelTests(unittest.TestCase):
    def test_cancel_moves_pending_to_cancelled(self):
        order = Order(500)
        order.cancel()
        self.assertEqual(
            order.summary(),
            {
                "state": "cancelled",
                "total_cents": 500,
                "refunded_cents": 0,
                "remaining_cents": 500,
            },
        )

    def test_repeated_cancel_is_rejected(self):
        order = Order(500)
        order.cancel()
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.summary()["state"], "cancelled")

    def test_cancel_captured_order_is_rejected(self):
        order = Order(500)
        order.capture()
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.summary()["state"], "paid")
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_cancel_partially_refunded_order_is_rejected(self):
        order = Order(500)
        order.capture()
        order.refund(100)
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.summary()["state"], "partially_refunded")

    def test_cancel_after_full_refund_is_rejected(self):
        order = Order(500)
        order.capture()
        order.refund(500)
        with self.assertRaises(ValueError):
            order.cancel()
        self.assertEqual(order.summary()["state"], "refunded")


class RefundStateTests(unittest.TestCase):
    def test_refund_pending_order_is_rejected(self):
        order = Order(500)
        with self.assertRaises(ValueError):
            order.refund(100)
        self.assertEqual(order.summary()["state"], "pending")
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_cancelled_order_is_rejected(self):
        order = Order(500)
        order.cancel()
        with self.assertRaises(ValueError):
            order.refund(100)
        self.assertEqual(order.summary()["state"], "cancelled")
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_after_full_refund_is_rejected(self):
        order = Order(500)
        order.capture()
        order.refund(500)
        with self.assertRaises(ValueError):
            order.refund(1)
        self.assertEqual(order.summary()["state"], "refunded")
        self.assertEqual(order.summary()["refunded_cents"], 500)


class RefundAmountTests(unittest.TestCase):
    def test_refund_zero_is_rejected(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(0)
        self.assertEqual(order.summary()["state"], "paid")
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_negative_is_rejected(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(-1)
        with self.assertRaises(ValueError):
            order.refund(-250)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_bool_is_rejected(self):
        # True/False are ints but must not be valid cent amounts.
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(True)
        with self.assertRaises(ValueError):
            order.refund(False)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_non_integer_is_rejected(self):
        order = Order(1000)
        order.capture()
        for bad in (1.0, 2.5, "100", None, [100]):
            with self.assertRaises(ValueError):
                order.refund(bad)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_exceeding_total_is_rejected(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(1001)
        self.assertEqual(order.summary()["refunded_cents"], 0)

    def test_refund_exceeding_remaining_balance_is_rejected(self):
        order = Order(1000)
        order.capture()
        order.refund(600)
        with self.assertRaises(ValueError):
            order.refund(401)
        # A rejected refund must not change the accumulated balance.
        self.assertEqual(
            order.summary(),
            {
                "state": "partially_refunded",
                "total_cents": 1000,
                "refunded_cents": 600,
                "remaining_cents": 400,
            },
        )


class RefundLifecycleTests(unittest.TestCase):
    def test_single_partial_refund_sets_partially_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(250)
        self.assertEqual(
            order.summary(),
            {
                "state": "partially_refunded",
                "total_cents": 1000,
                "refunded_cents": 250,
                "remaining_cents": 750,
            },
        )

    def test_multiple_partial_refunds_accumulate(self):
        order = Order(1000)
        order.capture()
        order.refund(100)
        order.refund(200)
        order.refund(300)
        self.assertEqual(
            order.summary(),
            {
                "state": "partially_refunded",
                "total_cents": 1000,
                "refunded_cents": 600,
                "remaining_cents": 400,
            },
        )

    def test_one_cent_below_total_stays_partial(self):
        order = Order(1000)
        order.capture()
        order.refund(999)
        self.assertEqual(order.summary()["state"], "partially_refunded")
        self.assertEqual(order.summary()["remaining_cents"], 1)

    def test_first_refund_may_equal_total(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        self.assertEqual(
            order.summary(),
            {
                "state": "refunded",
                "total_cents": 1000,
                "refunded_cents": 1000,
                "remaining_cents": 0,
            },
        )

    def test_partial_then_exact_remainder_becomes_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(250)
        order.refund(750)
        self.assertEqual(
            order.summary(),
            {
                "state": "refunded",
                "total_cents": 1000,
                "refunded_cents": 1000,
                "remaining_cents": 0,
            },
        )

    def test_exact_remainder_after_several_partials_becomes_refunded(self):
        order = Order(1000)
        order.capture()
        order.refund(1)
        order.refund(2)
        order.refund(3)
        order.refund(994)
        self.assertEqual(
            order.summary(),
            {
                "state": "refunded",
                "total_cents": 1000,
                "refunded_cents": 1000,
                "remaining_cents": 0,
            },
        )


class SummaryTests(unittest.TestCase):
    def test_summary_has_exact_documented_keys(self):
        self.assertEqual(
            set(Order(1000).summary()),
            {"state", "total_cents", "refunded_cents", "remaining_cents"},
        )

    def test_summary_remains_consistent_through_lifecycle(self):
        order = Order(2000)
        self.assertEqual(order.summary()["remaining_cents"], 2000)
        order.capture()
        self.assertEqual(order.summary()["remaining_cents"], 2000)
        order.refund(500)
        summary = order.summary()
        self.assertEqual(summary["state"], "partially_refunded")
        self.assertEqual(summary["remaining_cents"], 1500)
        self.assertEqual(
            summary["remaining_cents"],
            summary["total_cents"] - summary["refunded_cents"],
        )

    def test_remaining_cents_drops_after_full_refund(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        summary = order.summary()
        self.assertEqual(summary["remaining_cents"], 0)
        self.assertEqual(
            summary["remaining_cents"],
            summary["total_cents"] - summary["refunded_cents"],
        )

