import unittest
from decimal import Decimal

import solution


PAYLOAD = """
{"entries": [
  {"id": "b", "amount": "3.005", "quantity": 2, "at": "2026-01-02T03:04:05Z"},
  {"id": "a", "amount": "1.10", "at": "2026-01-01T00:00:00+00:00"}
]}
"""


class PublicTests(unittest.TestCase):
    def test_records_are_ordered_oldest_first(self):
        records = solution.normalise(PAYLOAD)
        self.assertEqual([record["id"] for record in records], ["a", "b"])

    def test_quantity_defaults_to_one(self):
        records = solution.normalise(PAYLOAD)
        self.assertEqual(records[0]["total"], Decimal("1.10"))

    def test_quantity_multiplies_the_amount(self):
        records = solution.normalise(PAYLOAD)
        self.assertEqual(records[1]["total"], Decimal("6.02"))

    def test_amounts_are_quantised_on_input(self):
        records = solution.normalise(PAYLOAD)
        self.assertEqual(records[1]["amount"], Decimal("3.01"))

    def test_timestamps_are_utc(self):
        records = solution.normalise(PAYLOAD)
        self.assertEqual(records[0]["at"].utcoffset().total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
