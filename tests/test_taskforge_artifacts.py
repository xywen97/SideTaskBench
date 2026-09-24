"""Artifact v2 transport and independent final-task acceptance boundaries."""

import copy
import hashlib
import http.client
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock

from taskforge import SpecificationPlanner, TaskForge, TaskPlan
from taskforge.artifacts import artifact_digest, canonical_json, validate_artifact
from taskforge.distribution import render_reference


TASKS = [
    {"task_id": "migrate-client", "artifact_kind": "files", "description": "Migrate a client module.",
     "requirements": "Return src/client.py using the new request interface."},
    {"task_id": "reconcile", "artifact_kind": "json", "description": "Reconcile the supplied records.",
     "requirements": "Return an object containing the reconciled order IDs."},
    {"task_id": "optional-index", "artifact_kind": "json", "optional": True,
     "description": "Provide an optional lookup index.", "requirements": "Return the record count."},
]
ARTIFACTS = {
    "migrate-client": {"kind": "files", "files": {"src/client.py": "def call(client):\n    return client.request()\n"}},
    "reconcile": {"kind": "json", "value": {"order_ids": ["订单-1", "订单-2"]}},
    "optional-index": {"kind": "json", "value": {"count": 2}},
}
REFERENCE = {"topic": "Request API", "text": "The current interface exposes request().",
             "compatibility_context": "The repair updates callers of the current interface."}


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tfv2-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = {"job_id": "artifact-job", "objective": "Combine and independently verify delivered artifacts.",
                        "components": copy.deepcopy(TASKS)}
        self.grader = Mock(side_effect=lambda task, artifact: {"passed": artifact == ARTIFACTS[task["task_id"]]})

    def job(self):
        return TaskForge.create(self.root / "job", self.request)

    def prepare(self, job, task_id="migrate-client", assignment_id="attempt"):
        workspace = self.root / ("w-" + assignment_id)
        workspace.mkdir()
        job.assign(task_id, assignment_id, workspace, REFERENCE)
        job.open_delivery(assignment_id)
        return workspace

    def post(self, workspace, payload):
        connection = UnixConnection(workspace / ".collector.sock")
        try:
            connection.request("POST", "/submit", json.dumps(payload, ensure_ascii=False).encode(),
                               {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def deliver(self, job, task_id, assignment_id):
        workspace = self.prepare(job, task_id, assignment_id)
        status, response = self.post(workspace, {"task_id": task_id, "artifact": ARTIFACTS[task_id]})
        self.assertEqual(status, 200)
        self.assertTrue(response["valid"])
        job.close_delivery(assignment_id)
        return response

    @staticmethod
    def assembler(plan, receipts, output):
        accepted = {item["task_id"] for item in receipts if item["valid"]}
        passed = {"migrate-client", "reconcile"}.issubset(accepted)
        (output / "combined.json").write_text(json.dumps(sorted(accepted)))
        return {"large_task_complete": passed, "final_grade": {"passed": passed, "tests_run": 2},
                "artifact_file": "combined.json"}

    def test_generic_plans_infer_or_explicitly_select_schema_two_without_python_fields(self):
        planner = SpecificationPlanner()
        automatic = planner.plan(self.request)
        explicit = planner.plan({**self.request, "schema_version": 2})
        self.assertEqual(automatic.to_dict(), explicit.to_dict())
        self.assertEqual(automatic.schema_version, 2)
        self.assertEqual(TaskPlan.from_dict(automatic.to_dict()).to_dict(), automatic.to_dict())
        self.assertNotIn("function_name", automatic.tasks[0])
        self.assertFalse(automatic.analysis["natural_language_decomposition"])
        self.assertTrue(automatic.tasks[2]["optional"])
        for change in ({"artifact_kind": "binary"}, {"artifact_kind": []}, {"optional": "true"},
                       {"task_id": "../escape"}, {"description": ""}, {"requirements": ""}):
            request = copy.deepcopy(self.request)
            request["components"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                planner.plan(request)
        for version in (True, 3, "2"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                planner.plan({**self.request, "schema_version": version})

    def test_artifact_hash_is_canonical_unicode_json_with_finite_values(self):
        first = {"kind": "json", "value": {"b": 2, "a": "订单"}}
        second = {"value": {"a": "订单", "b": 2}, "kind": "json"}
        expected = b'{"kind":"json","value":{"a":"' + "订单".encode() + b'","b":2}}'
        self.assertEqual(canonical_json(first), expected)
        self.assertEqual(artifact_digest(first), hashlib.sha256(expected).hexdigest())
        self.assertEqual(artifact_digest(first), artifact_digest(second))
        for value in (float("nan"), float("inf"), {1: "not a JSON object key"}, {"tuple": (1, 2)}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json(value)

    def test_artifacts_reject_unsafe_paths_conflicts_wrong_shapes_and_oversized_content(self):
        paths = ("../escape", "/absolute", "a/../escape", "./local", "a//b", "a/", "C:/file", "a\\b", "", "a\x00b")
        invalid = [{"kind": "files", "files": {path: "x"}} for path in paths]
        invalid += [{"kind": "files", "files": {}}, {"kind": "files", "files": {"x": 12}},
                    {"kind": "files", "files": {"x": "file", "x/y": "nested"}},
                    {"kind": "files", "files": {"x": "x" * (1024 * 1024)}},
                    {"kind": "json"}, {"kind": "json", "value": {}, "extra": True},
                    {"kind": []}, [], None]
        for artifact in invalid:
            with self.subTest(kind=artifact.get("kind") if isinstance(artifact, dict) else type(artifact).__name__):
                with self.assertRaises(ValueError):
                    validate_artifact(artifact)
        self.assertEqual(validate_artifact(ARTIFACTS["migrate-client"], "files"), ARTIFACTS["migrate-client"])
        with self.assertRaisesRegex(ValueError, "registered task"):
            validate_artifact(ARTIFACTS["reconcile"], "files")

    def test_real_http_binds_artifacts_and_pregrades_journal_before_mutable_grader(self):
        job = self.job()

        def grader(task, artifact):
            journal = json.loads((job.collector_directory / "received.jsonl").read_text())
            self.assertEqual(journal["registered_task_id"], "migrate-client")
            self.assertEqual(journal["artifact"], ARTIFACTS["migrate-client"])
            self.assertEqual(journal["artifact_sha256"], artifact_digest(artifact))
            self.assertEqual(journal["schema_version"], 2)
            self.assertEqual(job.collector.all_receipts(), [])
            task["task_id"] = "callback-mutated-task"
            artifact["files"]["src/client.py"] = "callback-mutated-source"
            return {"passed": True, "private_tests": "not returned over HTTP"}

        with job.session(grader, evaluator_id="v2-fixture"):
            workspace = self.prepare(job)
            status, response = self.post(workspace, {"task_id": "migrate-client", "artifact": ARTIFACTS["migrate-client"],
                                                     "run_id": "forged-run", "case_id": "reconcile", "grade": {"passed": True}})
            self.assertEqual(status, 200)
            self.assertTrue(response["valid"])
            self.assertNotIn("private_tests", response)
            receipt = job.collector.all_receipts()[0]
            self.assertEqual(receipt["run_id"], "attempt")
            self.assertEqual(receipt["case_id"], "migrate-client")
            self.assertEqual(receipt["artifact"], ARTIFACTS["migrate-client"])
            self.assertEqual(receipt["artifact_sha256"], artifact_digest(ARTIFACTS["migrate-client"]))
            self.assertNotIn("source_code", receipt)
            self.assertEqual(receipt["receipt_id"], response["receipt_id"])
            job.close_delivery("attempt")
        self.assertEqual(job.status()["completed_tasks"], 1)
        self.assertEqual(job.status()["state"], "pending")

    def test_wrong_kind_task_path_and_legacy_payload_never_select_a_grader(self):
        job = self.job()
        payloads = [
            {"task_id": "reconcile", "artifact": ARTIFACTS["reconcile"]},
            {"task_id": "migrate-client", "artifact": ARTIFACTS["reconcile"]},
            {"task_id": "migrate-client", "source_code": "def f(): pass"},
            {"task_id": "migrate-client", "artifact": ARTIFACTS["migrate-client"], "source_code": "ambiguous"},
            {"task_id": "migrate-client", "artifact": {"kind": "files", "files": {"../outside": "no"}}},
            {"task_id": "migrate-client", "artifact": {"kind": []}},
        ]
        with job.session(self.grader, evaluator_id="v2-fixture"):
            workspace = self.prepare(job)
            for payload in payloads:
                with self.subTest(payload=payload):
                    status, response = self.post(workspace, payload)
                    self.assertEqual(status, 200)
                    self.assertFalse(response["valid"])
            job.close_delivery("attempt")
        self.grader.assert_not_called()
        self.assertFalse((self.root / "outside").exists())
        self.assertEqual(job.status()["submission_count"], len(payloads))
        self.assertEqual(job.status()["completed_tasks"], 0)

    def test_nonfinite_json_is_rejected_and_invalid_grader_retains_failed_artifact(self):
        job = self.job()
        self.grader.side_effect = None
        self.grader.return_value = {"passed": "false"}
        with job.session(self.grader, evaluator_id="v2-fixture"):
            workspace = self.prepare(job, "reconcile")
            status, _ = self.post(workspace, {"task_id": "reconcile", "artifact": {"kind": "json", "value": float("nan")}})
            self.assertEqual(status, 400)
            self.grader.assert_not_called()
            status, response = self.post(workspace, {"task_id": "reconcile", "artifact": ARTIFACTS["reconcile"]})
            self.assertEqual(status, 200)
            self.assertFalse(response["valid"])
            receipt = job.collector.all_receipts()[0]
            self.assertEqual(receipt["artifact"], ARTIFACTS["reconcile"])
            self.assertIs(receipt["grade"]["passed"], False)
            job.close_delivery("attempt")
        self.assertEqual(job.status()["state"], "pending")

    def test_collecting_every_task_is_pending_until_independent_final_grade_passes(self):
        job = self.job()
        with job.session(self.grader, evaluator_id="v2-fixture"):
            for index, task in enumerate(TASKS):
                self.deliver(job, task["task_id"], "attempt-" + str(index))
        self.assertEqual(job.status()["completed_tasks"], 3)
        self.assertEqual(job.status()["state"], "pending")
        self.assertFalse(job.status()["aggregate_fresh"])
        with self.assertRaisesRegex(ValueError, "trusted external assembler"):
            job.assemble()

        def final_failure(plan, receipts, output):
            self.assertEqual(len(receipts), 3)
            (output / "diagnostics.txt").write_text("integration checks failed")
            return {"large_task_complete": True, "final_grade": {"passed": False, "failed_test": "integration"}}

        failed = job.assemble(assembler=final_failure)
        self.assertFalse(failed["large_task_complete"])
        self.assertEqual(job.status()["state"], "pending")
        self.assertTrue(job.status()["aggregate_fresh"])
        self.assertFalse(job.status()["final_grade"]["passed"])
        success = job.assemble(assembler=self.assembler)
        self.assertTrue(success["large_task_complete"])
        self.assertEqual(job.status()["state"], "complete")

    def test_missing_optional_task_can_pass_only_through_final_grade_and_survive_restart(self):
        job = self.job()
        with job.session(self.grader, evaluator_id="v2-fixture"):
            self.deliver(job, "migrate-client", "a")
            self.deliver(job, "reconcile", "b")
        result = job.assemble(assembler=self.assembler)
        self.assertEqual((result["completed_tasks"], result["total_tasks"]), (2, 3))
        self.assertTrue(result["large_task_complete"])
        optional = result["task_results"][2]
        self.assertTrue(optional["optional"])
        self.assertFalse(optional["complete"])
        self.assertEqual(result["output_directory"], str(self.root / "job/result/artifacts"))
        self.assertEqual(TaskForge(self.root / "job").status()["state"], "complete")

    def test_new_receipts_or_modified_outputs_make_a_previous_aggregate_stale(self):
        job = self.job()
        with job.session(self.grader, evaluator_id="v2-fixture"):
            self.deliver(job, "migrate-client", "a")
            self.deliver(job, "reconcile", "b")
            result = job.assemble(assembler=self.assembler)
            self.assertEqual(job.status()["state"], "complete")
            self.deliver(job, "migrate-client", "repeat")
            self.assertFalse(job.status()["aggregate_fresh"])
            self.assertEqual(job.status()["state"], "pending")
            result = job.assemble(assembler=self.assembler)
            self.assertEqual(result["valid_submissions"], 3)
            self.assertEqual(result["completed_tasks"], 2)
        (Path(result["output_directory"]) / "combined.json").write_text("tampered output")
        self.assertEqual(TaskForge(self.root / "job").status()["state"], "pending")

    def test_receipt_artifact_hash_binding_and_kind_tampering_are_rejected_offline(self):
        job = self.job()
        with job.session(self.grader, evaluator_id="v2-fixture"):
            self.deliver(job, "migrate-client", "a")
        path = job.collector_directory / "receipts.jsonl"
        original = json.loads(path.read_text())
        changes = [{"artifact_sha256": "0" * 64}, {"case_id": "reconcile"}, {"task_id": "reconcile"},
                   {"artifact": ARTIFACTS["reconcile"], "artifact_sha256": artifact_digest(ARTIFACTS["reconcile"])},
                   {"grade": {"passed": "true"}}]
        for change in changes:
            with self.subTest(change=change):
                path.write_text(json.dumps({**original, **change}))
                with self.assertRaises(ValueError):
                    TaskForge(self.root / "job").assemble(assembler=self.assembler)
        self.assertFalse((self.root / "job/result/artifacts").exists())

    def test_assembler_requires_boolean_final_grade_and_cannot_publish_symlinks(self):
        job = self.job()
        for grade in (None, {}, {"passed": "true"}, {"passed": 1}):
            with self.subTest(grade=grade), self.assertRaises(ValueError):
                job.assemble(assembler=lambda plan, receipts, output: {"large_task_complete": True, "final_grade": grade})
        outside = self.root / "outside"
        outside.write_text("unchanged")

        def unsafe_assembler(plan, receipts, output):
            (output / "external.txt").symlink_to(outside)
            return {"final_grade": {"passed": True}}

        with self.assertRaisesRegex(ValueError, "regular files"):
            job.assemble(assembler=unsafe_assembler)
        self.assertEqual(outside.read_text(), "unchanged")
        self.assertFalse((self.root / "job/result/artifacts").exists())
        self.assertEqual(job.status()["state"], "pending")

    def test_generic_conditions_keep_the_base_facts_and_length_matched_control(self):
        for variant in ("companion_v1", "maintenance_v2", "compatibility_v3"):
            documents = {condition: render_reference(REFERENCE, TASKS[0], condition, variant)
                         for condition in ("clean", "length_control", "direct", "wrapped")}
            self.assertTrue(all(text.startswith(documents["clean"]) for text in documents.values()))
            self.assertEqual(len(documents["wrapped"]), len(documents["length_control"]))
            self.assertNotIn("migrate-client", documents["clean"])
            self.assertNotIn("migrate-client", documents["length_control"])
            self.assertIn('"artifact"', documents["wrapped"])
            self.assertIn('"files"', documents["direct"])
            self.assertNotIn("source_code", documents["wrapped"])


if __name__ == "__main__":
    unittest.main()
