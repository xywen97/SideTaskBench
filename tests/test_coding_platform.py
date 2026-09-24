"""Runner/TaskForge contract tests; no LLM or candidate code is executed."""

from copy import deepcopy
import hashlib
import http.client
import json
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from microcoder.config import Settings
from compute_bench.coding.documents import CONDITIONS, VARIANTS, reference_context, render_reference
from compute_bench.coding.platform import EVALUATOR_ID, open_platform
from compute_bench.coding.runner import execute_coding, resume_coding
from compute_bench.coding.tasks import build_coding_cases
from taskforge import TaskForge


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class CodingPlatformTests(unittest.TestCase):
    def test_platform_plans_only_public_contracts_and_preserves_every_reference_treatment(self):
        cases = build_coding_cases(6)
        with tempfile.TemporaryDirectory(prefix="cbp-") as temporary:
            root = Path(temporary)
            platform = open_platform(root, cases)
            request = json.loads((root / "platform/request.json").read_text())
            self.assertEqual(set(request), {"job_id", "objective", "components"})
            self.assertEqual(request["components"], [case["crowd_task"] for case in cases])
            self.assertEqual(platform.plan["tasks"], request["components"])
            for case in cases:
                self.assertNotIn(case["crowd_reference_code"], (root / "platform/request.json").read_text())
                for condition in CONDITIONS:
                    for variant in VARIANTS:
                        attempt = f"{case['id']}-{condition}-{variant}"
                        workspace = root / "workspaces" / attempt
                        workspace.mkdir(parents=True)
                        assignment = platform.assign(case["crowd_task"]["task_id"], attempt, workspace,
                                                     reference_context(case), condition=condition,
                                                     variant=variant, routing_id=case["id"])
                        expected = render_reference(case, condition, variant).encode()
                        self.assertEqual((workspace / "docs/reference.md").read_bytes(), expected)
                        self.assertEqual(assignment["reference_sha256"], hashlib.sha256(expected).hexdigest())
                        self.assertEqual(assignment["task_id"], case["crowd_task"]["task_id"])
                        self.assertEqual(assignment["routing_id"], case["id"])
            self.assertEqual(open_platform(root, cases).plan, platform.plan)
            changed = deepcopy(cases)
            changed[0]["crowd_task"]["description"] += " A different contract."
            with self.assertRaisesRegex(ValueError, "does not match"):
                open_platform(root, changed)

    def test_historical_deliveries_cannot_be_relabelled_as_platform_assignments(self):
        cases = build_coding_cases(1)
        for filename in ("receipts.jsonl", "received.jsonl", "blocked.jsonl"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory(prefix="cbp-") as temporary:
                root = Path(temporary)
                (root / "collector").mkdir()
                path = root / "collector" / filename
                path.write_text('{"retained":"historical evidence"}\n')
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "historical receipts"):
                    open_platform(root, cases)
                self.assertFalse((root / "platform").exists())
                self.assertEqual(path.read_bytes(), before)

    def test_runner_persists_assignments_and_assembles_the_same_received_sources(self):
        cases = build_coding_cases(2)
        expected_sources = {case["id"]: case["crowd_reference_code"] for case in cases}

        def bootstrap(case, workspace, condition, variant):
            workspace.mkdir(parents=True)
            for relative, text in case["repo_files"].items():
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)

        def environment(case, workspace, condition, **kwargs):
            return SimpleNamespace(events=[], workspace=workspace, case=case)

        def fake_agent(agent, task, trace_path):
            case, workspace = agent.tools.case, agent.tools.workspace
            self.assertEqual(task, case["user_task"])
            connection = UnixConnection(workspace / ".collector.sock")
            try:
                connection.request("POST", "/submit", json.dumps({
                    "task_id": case["crowd_task"]["task_id"], "source_code": expected_sources[case["id"]],
                }), {"Content-Type": "application/json"})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertTrue(json.loads(response.read())["valid"])
            finally:
                connection.close()
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text('{"kind":"synthetic-platform-test"}\n')
            return {
                "status": "completed", "error": None, "final_content": "synthetic result",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "reasoning_tokens": 0},
                "llm_calls": 1, "tool_calls": 0, "latency_seconds": 0.1,
                "api_response_ids": ["synthetic-" + trace_path.stem], "trace_file": str(trace_path),
            }

        with tempfile.TemporaryDirectory(prefix="cbp-") as temporary, \
             patch("compute_bench.coding.runner.Sandbox") as sandbox, \
             patch("compute_bench.coding.runner.create_workspace", side_effect=bootstrap), \
             patch("compute_bench.coding.runner.ChatClient") as client, \
             patch("compute_bench.coding.runner.CodingEnvironment", side_effect=environment), \
             patch("compute_bench.coding.runner.CodingAgent.run", autospec=True, side_effect=fake_agent) as agent, \
             patch("compute_bench.coding.runner.grade_main", return_value={"passed": True}), \
             patch("compute_bench.coding.runner.scan_work", return_value=[]), \
             patch("compute_bench.coding.platform.grade_crowd", return_value={"passed": True}) as grader, \
             patch("builtins.print"):
            root = Path(temporary)
            settings = Settings(api_key="synthetic-test-key", model="test-model")
            sandbox.probe.return_value = {"backend": "synthetic", "available": True}
            sandbox.return_value.run.return_value = {"stdout": "synthetic patch", "stderr": "", "exit_code": 0}
            summary = execute_coding(settings, root, count=2, conditions=["wrapped"], repeats=1, workers=2)
            self.assertTrue(summary["all_planned_recorded"])
            self.assertEqual(agent.call_count, 2)
            self.assertEqual(client.call_count, 2)
            self.assertEqual(grader.call_count, 2)
            for call in grader.call_args_list:
                case, source = call.args
                self.assertEqual(case, cases[int(case["id"].split("-")[-1]) - 1])
                self.assertEqual(source, expected_sources[case["id"]])

            platform = TaskForge(root / "platform")
            assignments = {item["assignment_id"]: item for item in platform.status()["assignments"]}
            delivery = json.loads((root / "platform/delivery.json").read_text())
            self.assertEqual(delivery["evaluator_id"], EVALUATOR_ID)
            self.assertEqual(delivery["bindings"], {case["id"]: case["crowd_task"]["task_id"] for case in cases})
            records = [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines()]
            for result in records:
                assignment = assignments[result["run_id"]]
                self.assertEqual(assignment["routing_id"], result["case_id"])
                self.assertEqual(assignment["task_id"], result["crowd_task_id"])
                self.assertEqual(assignment["workspace"], result["workspace"])
                self.assertEqual(assignment["state"], "closed")
                self.assertTrue(result["valid_delivery"])
                self.assertTrue(result["joint_success"])
                self.assertFalse((Path(result["workspace"]) / ".collector.sock").exists())

            legacy = json.loads((root / "collected_library.json").read_text())
            assembled = json.loads((root / "platform/result.json").read_text())
            for key in ("completed_tasks", "total_tasks", "valid_submissions", "submission_count", "large_task_complete"):
                self.assertEqual(legacy[key], assembled[key])
            self.assertTrue(assembled["large_task_complete"])
            for left, right in zip(legacy["task_results"], assembled["task_results"]):
                self.assertEqual({k: v for k, v in left.items() if k != "source_file"},
                                 {k: v for k, v in right.items() if k != "source_file"})
                self.assertEqual(Path(left["source_file"]).read_bytes(), Path(right["source_file"]).read_bytes())

            # Missing result records must never cause a closed assignment to rerun.
            (root / "results.jsonl").write_text("")
            for result in records:
                Path(result["trace_file"]).unlink()
            before = (root / "manifest.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "Closed platform assignments"):
                resume_coding(settings, root, workers=1)
            self.assertEqual((root / "manifest.json").read_bytes(), before)
            self.assertEqual(agent.call_count, 2)
            self.assertFalse((root / "recovery_1").exists())


if __name__ == "__main__":
    unittest.main()
