"""Coding/TaskForge v2 integration checks."""

from copy import deepcopy
import http.client
import json
from pathlib import Path
import socket
import tempfile
import unittest

from compute_bench.workloads.provider_atomic import public_atomic_tasks
from compute_bench.coding.documents import reference_context, render_reference
from compute_bench.coding.platform import assemble_platform, delivery_session, open_platform, public_request
from compute_bench.coding.tasks import build_coding_cases
from taskforge.distribution import CONDITIONS, VARIANTS


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class CodingPlatformTests(unittest.TestCase):
    def test_plan_has_all_thirty_public_units_and_references_expose_one(self):
        cases = build_coding_cases()
        with tempfile.TemporaryDirectory(prefix="cbp-") as temporary:
            root = Path(temporary)
            platform = open_platform(root, cases)
            request = public_request(cases)
            self.assertEqual(request["components"], public_atomic_tasks())
            self.assertEqual(len(platform.plan["tasks"]), 30)
            serialized = (root / "platform/request.json").read_text()
            for case in cases:
                self.assertNotIn(json.dumps(case["crowd_reference_artifact"]), serialized)
            case = cases[0]
            for condition in CONDITIONS:
                for variant in VARIANTS:
                    attempt = f"{condition}-{variant}"
                    workspace = root / attempt
                    workspace.mkdir()
                    assignment = platform.assign(case["crowd_task"]["task_id"], attempt, workspace,
                                                 reference_context(case), condition=condition,
                                                 variant=variant, routing_id=case["id"])
                    self.assertEqual((workspace / "docs/reference.md").read_text(),
                                     render_reference(case, condition, variant))
                    self.assertEqual(assignment["task_id"], case["crowd_task"]["task_id"])
            changed = deepcopy(cases)
            changed[0]["crowd_task"]["description"] += " changed"
            # The global catalog, not a mutable case copy, is the frozen public plan.
            self.assertEqual(open_platform(root, changed).plan, platform.plan)

    def test_real_generic_delivery_and_partial_portfolio_assembly(self):
        cases = build_coding_cases(1)
        case = cases[0]
        with tempfile.TemporaryDirectory(prefix="cbp-") as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            platform = open_platform(root, cases)
            platform.assign(case["crowd_task"]["task_id"], "run-1", workspace,
                            reference_context(case), routing_id=case["id"])
            with delivery_session(platform, cases):
                platform.open_delivery("run-1")
                connection = UnixConnection(workspace / ".collector.sock")
                connection.request("POST", "/submit", json.dumps({
                    "task_id": case["crowd_task"]["task_id"],
                    "artifact": case["crowd_reference_artifact"],
                }), {"Content-Type": "application/json"})
                response = connection.getresponse()
                body = json.loads(response.read())
                connection.close()
                self.assertTrue(body["valid"])
                platform.close_delivery("run-1")
                result = assemble_platform(platform)
            self.assertEqual(result["completed_tasks"], 1)
            self.assertEqual(result["total_tasks"], 30)
            self.assertEqual(result["effective_work_units"], 1)
            self.assertFalse(result["large_task_complete"])
            self.assertEqual(result["coverage"], 1 / 30)
            self.assertEqual(result["value_units_delivered"], 1)

    def test_legacy_source_payload_is_not_a_generic_artifact(self):
        cases = build_coding_cases(1)
        case = cases[0]
        with tempfile.TemporaryDirectory(prefix="cbp-") as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            platform = open_platform(root, cases)
            platform.assign(case["crowd_task"]["task_id"], "run-1", workspace,
                            reference_context(case), routing_id=case["id"])
            with delivery_session(platform, cases):
                platform.open_delivery("run-1")
                connection = UnixConnection(workspace / ".collector.sock")
                connection.request("POST", "/submit", json.dumps({
                    "task_id": case["crowd_task"]["task_id"], "source_code": "pass",
                }), {"Content-Type": "application/json"})
                response = connection.getresponse()
                self.assertFalse(json.loads(response.read())["valid"])
                connection.close()
                platform.close_delivery("run-1")


if __name__ == "__main__":
    unittest.main()
