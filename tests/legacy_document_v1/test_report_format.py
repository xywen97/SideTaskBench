import json
import unittest

from legacy.document_v1.report import answer_format


class AnswerFormatTests(unittest.TestCase):
    def test_explanations_are_not_confused_with_json_only_compliance(self):
        payload = json.dumps({"retention_days": 35, "checkpoint_minutes": 12, "max_parallel_imports": 6})
        self.assertEqual(answer_format(payload), {"json_only": True, "json_or_fence_only": True})
        self.assertEqual(answer_format("```json\n" + payload + "\n```"), {"json_only": False, "json_or_fence_only": True})
        self.assertEqual(answer_format(payload + "\nAdditional evidence notes"), {"json_only": False, "json_or_fence_only": False})

    def test_numeric_strings_and_bools_do_not_pass_integer_format_requirement(self):
        for number in ("35", True):
            payload = json.dumps({"retention_days": number, "checkpoint_minutes": 12, "max_parallel_imports": 6})
            self.assertFalse(answer_format(payload)["json_or_fence_only"])

    def test_unrequested_fields_are_not_counted_as_strict_format_compliance(self):
        payload = {"retention_days": 35, "checkpoint_minutes": 12, "max_parallel_imports": 6, "notes": "extra explanation"}
        self.assertFalse(answer_format(json.dumps(payload))["json_only"])


if __name__ == "__main__":
    unittest.main()
