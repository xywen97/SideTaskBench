import json, unittest
from order_service import Order
SCENARIOS = []

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
