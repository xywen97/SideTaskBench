import json, unittest
from order_service import Order
SCENARIOS = [{'total_cents': 100, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': True}], 'expected': {'error': 'ValueError', 'at_step': 1}}, {'total_cents': 250, 'actions': [{'op': 'capture'}, {'op': 'capture'}], 'expected': {'error': 'ValueError', 'at_step': 1}}, {'total_cents': 100, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': 100}], 'expected': {'state': 'refunded', 'total_cents': 100, 'refunded_cents': 100, 'remaining_cents': 0}}, {'total_cents': 5000, 'actions': [{'op': 'capture'}, {'op': 'cancel'}], 'expected': {'error': 'ValueError', 'at_step': 1}}, {'total_cents': 100, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': 40}], 'expected': {'state': 'partially_refunded', 'total_cents': 100, 'refunded_cents': 40, 'remaining_cents': 60}}, {'total_cents': 1000, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': 300}, {'op': 'refund', 'amount': 200}], 'expected': {'state': 'partially_refunded', 'total_cents': 1000, 'refunded_cents': 500, 'remaining_cents': 500}}, {'total_cents': 100, 'actions': [{'op': 'refund', 'amount': 1}], 'expected': {'error': 'ValueError', 'at_step': 0}}, {'total_cents': 100, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': 30}, {'op': 'refund', 'amount': 30}, {'op': 'refund', 'amount': 41}], 'expected': {'error': 'ValueError', 'at_step': 3}}, {'total_cents': 100, 'actions': [{'op': 'capture'}, {'op': 'refund', 'amount': 0}], 'expected': {'error': 'ValueError', 'at_step': 1}}]

class AtomicRegressionTests(unittest.TestCase):
    def test_scenarios(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                order = Order(scenario["total_cents"])
                actual = None
                for index, action in enumerate(scenario["actions"]):
                    try:
                        if action["op"] == "capture": order.capture()
                        elif action["op"] == "cancel": order.cancel()
                        else: order.refund(action["amount"])
                    except ValueError:
                        actual = {"error": "ValueError", "at_step": index}
                        break
                if actual is None: actual = order.summary()
                self.assertEqual(json.dumps(actual, sort_keys=True), json.dumps(scenario["expected"], sort_keys=True))
