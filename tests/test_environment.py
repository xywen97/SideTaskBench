"""Check document exposure accounting and the real network tool boundary."""

import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from compute_bench.collector import Collector
from compute_bench.environment import LocalEnvironment
from compute_bench.scenarios import build_cases


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.case = build_cases(1)[0]
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.collector = Collector(Path(self.directory.name), [self.case]).start()
        self.addCleanup(self.collector.close)
        self.collector.register_run("agent-run", self.case["id"])

    def environment(self, **kwargs):
        return LocalEnvironment(self.case, "wrapped", "agent-run", self.collector.url, **kwargs)

    def test_forced_first_search_lists_source_first_and_read_records_exposure(self):
        environment = self.environment()
        result = environment.execute("search", {"query": self.case["query"]})
        self.assertEqual(result["results"][0]["document_id"], environment.third_party_document_id)
        self.assertFalse(environment.events[-1]["exposed"])
        document = environment.execute("read_document", {"document_id": result["results"][0]["document_id"]})
        self.assertIn("submit_result", document["text"])
        self.assertTrue(environment.events[-1]["exposed"])
        self.assertNotIn("crowd_gold", document)
        self.assertNotIn("expected_answer", document)

    def test_natural_search_preserves_all_readable_documents(self):
        environment = self.environment(exposure="natural")
        result = environment.execute("search", {"query": self.case["query"]})
        ids = {item["document_id"] for item in result["results"]}
        self.assertEqual(ids, {doc["id"] for doc in self.case["documents"]} | {environment.third_party_document_id})
        for doc in self.case["documents"]:
            self.assertIn("text", environment.execute("read_document", {"document_id": doc["id"]}))
            self.assertFalse(environment.events[-1]["exposed"])

    def test_submit_result_reaches_collector_with_bound_run_id(self):
        environment = self.environment()
        result = environment.execute("submit_result", self.case["crowd_gold"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["run_id"], "agent-run")
        self.assertEqual(len(self.collector.get_receipts("agent-run")), 1)

    def test_egress_defense_blocks_actual_http_delivery(self):
        environment = self.environment(defense="egress")
        with patch("compute_bench.environment.http.client.HTTPConnection") as http:
            result = environment.execute("submit_result", self.case["crowd_gold"])
        self.assertTrue(result["blocked"])
        self.assertTrue(environment.events[-1]["blocked"])
        http.assert_not_called()
        self.assertEqual(self.collector.get_receipts("agent-run"), [])

    def test_external_urls_credentials_and_destination_parameters_are_rejected(self):
        for url in ("https://example.com:443", "http://8.8.8.8:80", "http://localhost:80",
                    "http://127.0.0.1:80/other", "http://user@127.0.0.1:80",
                    "http://127.0.0.1:80?redirect=https://example.com", "file:///tmp/data"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LocalEnvironment(self.case, "wrapped", "agent-run", url)
        environment = self.environment()
        result = environment.execute("submit_result", self.case["crowd_gold"] | {"url": "https://example.com"})
        self.assertIn("error", result)
        result = environment.execute("submit_result", self.case["crowd_gold"] | {"run_id": "someone-else"})
        self.assertIn("error", result)
        self.assertEqual(self.collector.aggregate()["submission_count"], 0)

    def test_loopback_redirect_is_not_followed(self):
        class RedirectHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", "https://example.com/should-never-be-requested")
                self.send_header("Content-Length", "0")
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            environment = LocalEnvironment(self.case, "wrapped", "agent-run",
                                           f"http://127.0.0.1:{server.server_address[1]}")
            result = environment.execute("submit_result", self.case["crowd_gold"])
            self.assertEqual(result["http_status"], 302)
            self.assertIn("error", result)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_arbitrary_file_access_and_shell_tools_are_unavailable(self):
        environment = self.environment()
        for path in ("/etc/passwd", "../../.env", "file:///etc/passwd"):
            self.assertIn("error", environment.execute("read_document", {"document_id": path}))
        self.assertIn("error", environment.execute("shell", {"command": "pwd"}))
        self.assertTrue(environment.events[-1]["blocked"])
        self.assertEqual({tool["function"]["name"] for tool in environment.tools},
                         {"search", "read_document", "submit_result"})


if __name__ == "__main__":
    unittest.main()
