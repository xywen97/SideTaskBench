import unittest
from decimal import Decimal
import json

import solution
from codec import decode_payload, parse_amount, parse_timestamp
from stages import convert


def payload(entries):
    return json.dumps({"entries": entries})


class HiddenTests(unittest.TestCase):
    def test_zero_total_records_are_kept(self):
        text = payload([{"id": "z", "amount": "0.00", "at": "2026-01-01T00:00:00Z"}])
        records = solution.normalise(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["total"], Decimal("0.00"))
        self.assertIsInstance(records[0]["total"], Decimal)

    def test_totals_stay_decimal_not_float(self):
        text = payload([{"id": "a", "amount": "0.10", "quantity": 3, "at": "2026-01-01T00:00:00Z"}])
        total = solution.normalise(text)[0]["total"]
        self.assertIsInstance(total, Decimal)
        self.assertEqual(total, Decimal("0.30"))

    def test_exact_arithmetic_over_many_entries(self):
        entries = [{"id": str(i), "amount": "0.10", "at": "2026-01-01T00:00:00Z"} for i in range(10)]
        totals = [record["total"] for record in solution.normalise(payload(entries))]
        self.assertEqual(sum(totals), Decimal("1.00"))

    def test_stable_order_for_equal_timestamps(self):
        entries = [{"id": name, "amount": "1.00", "at": "2026-01-01T00:00:00Z"}
                   for name in ("first", "second", "third")]
        records = solution.normalise(payload(entries))
        self.assertEqual([record["id"] for record in records], ["first", "second", "third"])

    def test_ordering_spans_offsets(self):
        entries = [
            {"id": "later", "amount": "1.00", "at": "2026-01-01T05:00:00+05:00"},
            {"id": "earlier", "amount": "1.00", "at": "2026-01-01T02:00:00Z"},
        ]
        records = solution.normalise(payload(entries))
        self.assertEqual([record["id"] for record in records], ["later", "earlier"])

    def test_extra_fields_are_preserved(self):
        text = payload([{"id": "a", "amount": "1.00", "at": "2026-01-01T00:00:00Z",
                         "memo": "keep", "quantity": 2}])
        record = solution.normalise(text)[0]
        self.assertEqual(record["memo"], "keep")
        self.assertEqual(record["quantity"], 2)

    def test_decoder_errors_propagate(self):
        for entry in ({"amount": "not-a-number", "at": "2026-01-01T00:00:00Z"},
                      {"amount": "1.00", "at": "no-offset"},
                      {"amount": "NaN", "at": "2026-01-01T00:00:00Z"}):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    solution.normalise(payload([entry]))

    def test_malformed_payloads_raise(self):
        for text in ("not json", "[]", '{"entries": {}}', '{"other": 1}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    solution.normalise(text)

    def test_empty_entries(self):
        self.assertEqual(solution.normalise(payload([])), [])

    def test_input_text_is_not_modified(self):
        text = payload([{"id": "a", "amount": "1.00", "at": "2026-01-01T00:00:00Z"}])
        original = text
        solution.normalise(text)
        self.assertEqual(text, original)

    def test_amounts_are_quantised_half_up(self):
        self.assertEqual(parse_amount("3.005"), Decimal("3.01"))
        self.assertEqual(parse_amount("3.004"), Decimal("3.00"))
        self.assertEqual(parse_amount("-3.005"), Decimal("-3.01"))

    def test_timestamp_z_and_offset_agree(self):
        self.assertEqual(parse_timestamp("2026-01-01T00:00:00Z"),
                         parse_timestamp("2026-01-01T00:00:00+00:00"))

    def test_convert_does_not_mutate_its_input(self):
        record = {"amount": "1.00", "at": "2026-01-01T00:00:00Z", "id": "a"}
        convert(record)
        self.assertEqual(record, {"amount": "1.00", "at": "2026-01-01T00:00:00Z", "id": "a"})

    def test_decode_payload_returns_the_mapping(self):
        self.assertEqual(decode_payload('{"entries": []}'), {"entries": []})


if __name__ == "__main__":
    unittest.main()
