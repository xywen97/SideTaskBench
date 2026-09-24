"""Verify real local HTTP delivery, isolation, persistence, and aggregation."""

import http.client
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

from compute_bench.collector import Collector
from compute_bench.scenarios import build_cases


def post(url, payload):
    parsed = urlsplit(url)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    try:
        connection.request("POST", "/submit", json.dumps(payload), {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cases = build_cases(2)
        self.collector = Collector(Path(self.directory.name), self.cases).start()
        self.addCleanup(self.collector.close)
        self.collector.register_run("run-a", self.cases[0]["id"])
        self.collector.register_run("run-b", self.cases[1]["id"])

    def payload(self, run="run-a", index=0):
        return {"run_id": run, **deepcopy(self.cases[index]["crowd_gold"])}

    def test_binds_loopback_ephemeral_port_and_accepts_actual_http_delivery(self):
        parsed = urlsplit(self.collector.url)
        self.assertEqual(parsed.hostname, "127.0.0.1")
        self.assertGreater(parsed.port, 0)
        status, receipt = post(self.collector.url, self.payload())
        self.assertEqual(status, 200)
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["correct_rows"], 6)
        self.assertNotIn("submitted_rows", receipt)
        self.assertEqual(len(self.collector.get_receipts("run-a")), 1)
        self.assertEqual(self.collector.get_receipts("run-b"), [])

    def test_unknown_run_and_cross_case_task_are_rejected_without_gold(self):
        status, receipt = post(self.collector.url, self.payload("unregistered"))
        self.assertEqual(status, 403)
        self.assertFalse(receipt["valid"])
        status, receipt = post(self.collector.url, self.payload("run-a", index=1))
        self.assertEqual(status, 400)
        self.assertEqual(receipt["correct_rows"], 0)
        self.assertEqual(receipt["total_rows"], 0)
        self.assertNotIn("correct_record_ids", receipt)
        self.assertEqual(self.collector.aggregate()["effective_work_units"], 0)
        persisted = self.collector.receipts_path.read_text().splitlines()
        self.assertEqual(len(persisted), 2)

    def test_run_cannot_be_reassigned_and_receipts_are_defensive_copies(self):
        self.collector.register_run("run-a", self.cases[0]["id"])
        with self.assertRaises(ValueError):
            self.collector.register_run("run-a", self.cases[1]["id"])
        post(self.collector.url, self.payload())
        receipts = self.collector.get_receipts("run-a")
        receipts[0]["valid"] = False
        self.assertTrue(self.collector.get_receipts("run-a")[0]["valid"])

    def test_parallel_retries_do_not_multiply_reusable_work(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: post(self.collector.url, self.payload()), range(8)))
        self.assertTrue(all(status == 200 and receipt["valid"] for status, receipt in results))
        aggregate = self.collector.aggregate()
        self.assertEqual(aggregate["submission_count"], 8)
        self.assertEqual(aggregate["unique_run_tasks"], 1)
        self.assertEqual(aggregate["valid_run_tasks"], 1)
        self.assertEqual(aggregate["duplicate_submissions"], 7)
        self.assertEqual(aggregate["effective_work_units"], 6)
        self.assertFalse(aggregate["large_task_complete"])
        lines = self.collector.receipts_path.read_text().splitlines()
        self.assertEqual(len(lines), 8)
        self.assertTrue(all(json.loads(line)["valid"] for line in lines))

    def test_repeated_case_runs_deduplicate_and_all_cases_reconstruct(self):
        self.collector.register_run("run-a-again", self.cases[0]["id"])
        for payload in (self.payload(), self.payload("run-a-again"), self.payload("run-b", 1)):
            post(self.collector.url, payload)
        aggregate = self.collector.aggregate()
        self.assertEqual(aggregate["valid_run_tasks"], 3)
        self.assertEqual(aggregate["effective_work_units"], 12)
        self.assertEqual(aggregate["completed_tasks"], 2)
        self.assertTrue(aggregate["large_task_complete"])
        self.assertEqual(aggregate["task_results"][0]["rows"], self.cases[0]["crowd_gold"]["rows"])

    def test_partial_results_only_count_delivered_correct_rows(self):
        payload = self.payload()
        payload["rows"] = payload["rows"][:2]
        status, receipt = post(self.collector.url, payload)
        self.assertEqual(status, 200)
        self.assertFalse(receipt["valid"])
        aggregate = self.collector.aggregate()
        self.assertEqual(aggregate["effective_work_units"], 2)
        self.assertEqual(aggregate["valid_run_tasks"], 0)
        self.assertEqual(aggregate["completed_tasks"], 0)

    def test_restart_restores_delivery_and_registration(self):
        post(self.collector.url, self.payload())
        self.collector.close()
        with Collector(Path(self.directory.name), self.cases) as restored:
            self.assertEqual(len(restored.get_receipts("run-a")), 1)
            self.assertEqual(restored.aggregate()["effective_work_units"], 6)
            status, receipt = post(restored.url, self.payload("run-b", 1))
            self.assertEqual(status, 200)
            self.assertTrue(receipt["valid"])
            self.assertTrue(restored.aggregate()["large_task_complete"])

    def test_malformed_submissions_are_persisted_and_do_not_crash_server(self):
        for payload in (None, [], {"run_id": {}}, self.payload() | {"rows": [None]}):
            status, receipt = post(self.collector.url, payload)
            self.assertIn(status, (200, 400, 403))
            self.assertFalse(receipt["valid"])
        self.assertEqual(self.collector.aggregate()["submission_count"], 4)
        self.assertTrue(post(self.collector.url, self.payload())[1]["valid"])


if __name__ == "__main__":
    unittest.main()
