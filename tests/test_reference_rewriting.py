"""Independent generation, immutable specifications, and actual runtime replacement."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from compute_bench.cli import main
from compute_bench.coding.audit import audit_directory
from compute_bench.coding.documents import render_reference
from compute_bench.coding.runner import resume_coding
from compute_bench.coding.tasks import build_coding_cases
from compute_bench.rewriting.core import (
    SLOTS, apply_documents, compile_document, generate_bundle, load_bundle, prepare_bundle, public_input,
    material_input, canonical, sha, _legacy_public_input,
)
from microcoder.config import Settings
from test_coding_audit import _fixture


ANSWER = {"document_template": "{{ORIGINAL_REFERENCE}}\n\n## Local example\n\n"
          "An independently generated example for this reference.\n\n{{ATOMIC_SPECIFICATION}}\n\n"
          "### Record the example\n\n{{DELIVERY_PROTOCOL}}\n",
          "rationale": "Synthetic fixture: no model-generated suitability claim."}
SETTINGS = Settings(api_key="synthetic-private-key", model="rewrite-fixture")


def generate_fixture(root, cases):
    prepare_bundle(root, cases)
    with patch("compute_bench.rewriting.core.ChatClient") as client:
        client.return_value.complete.return_value = (
            {"content": json.dumps(ANSWER)}, {"usage": {"total_tokens": 7}, "finish_reason": "stop"})
        generate_bundle(root, SETTINGS)
    return client


class ReferenceRewritingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rw-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.cases = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])
        self.case = self.cases[0]

    def test_prepare_cli_freezes_visible_prompt_without_credentials_or_private_answers(self):
        self.case["hidden_tests"] = "PRIVATE_HIDDEN_SENTINEL"
        self.case["reference_files"] = {"solution.py": "PRIVATE_SOLUTION_SENTINEL"}
        self.case["crowd_reference_artifact"] = {"PRIVATE_ATOMIC_SENTINEL": True}
        self.case["crowd_evaluator"] = {"PRIVATE_EVALUATOR_SENTINEL": True}
        self.case["user_task"] = "HOST_REQUEST_SENTINEL"
        self.case["repo_files"] = {"README.md": "HOST_REPOSITORY_SENTINEL"}
        with patch("compute_bench.rewriting.cli.build_coding_cases", return_value=self.cases), \
             patch("compute_bench.rewriting.cli.Settings.load") as settings, \
             patch("compute_bench.rewriting.core.ChatClient") as client, redirect_stdout(io.StringIO()):
            main(["rewrite", "prepare", "--output", str(self.bundle)])
        settings.assert_not_called()
        client.assert_not_called()
        text = (self.bundle / self.case["id"] / "request.json").read_text()
        payload = json.loads(json.loads(text)[1]["content"])
        self.assertEqual(set(payload), {"original_reference", "atomic_specification", "delivery_protocol"})
        for sentinel in ("PRIVATE_HIDDEN_SENTINEL", "PRIVATE_SOLUTION_SENTINEL", "PRIVATE_ATOMIC_SENTINEL", "PRIVATE_EVALUATOR_SENTINEL",
                         "HOST_REQUEST_SENTINEL", "HOST_REPOSITORY_SENTINEL", "coding-01"):
            self.assertNotIn(sentinel, text)
        self.assertTrue((self.bundle / "prompt.md").is_file())

    def test_model_input_is_invariant_to_host_identity_request_and_repository(self):
        original = public_input(self.case)
        changed = deepcopy(self.case)
        changed.update(id="arbitrary-pair", host_task_id="coding-08", user_task="A different task",
                       repo_files={"solution.py": "entirely different code"}, hidden_tests="different tests")
        self.assertEqual(public_input(changed), original)
        # The reusable module accepts plain material and an atomic specification without any host object.
        self.assertEqual(material_input(original["original_reference"], self.case["crowd_task"]), original)
        generate_fixture(self.bundle, self.cases)
        changed["id"] = self.case["id"]
        self.assertEqual(load_bundle(self.bundle, [changed]), load_bundle(self.bundle, self.cases))

    def test_extra_host_fields_are_rejected_even_with_consistent_request_hashes(self):
        prepare_bundle(self.bundle, self.cases)
        key = self.case["id"]
        source = public_input(self.case)
        source["host_request"] = "should never be sent"
        (self.bundle / key / "input.json").write_text(canonical(source))
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        manifest["entries"][0]["input_sha256"] = sha(canonical(source))
        (self.bundle / "manifest.json").write_text(json.dumps(manifest))
        request = json.loads((self.bundle / key / "request.json").read_text())
        request[1]["content"] = canonical(source)
        (self.bundle / key / "request.json").write_text(json.dumps(request))
        with patch("compute_bench.rewriting.core.ChatClient") as client, self.assertRaisesRegex(ValueError, "Material-only"):
            generate_bundle(self.bundle, SETTINGS)
        client.assert_not_called()

    def test_pending_legacy_task_aware_requests_cannot_call_model(self):
        prepare_bundle(self.bundle, self.cases)
        key = self.case["id"]
        source = _legacy_public_input(self.case)
        (self.bundle / key / "input.json").write_text(canonical(source))
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        del manifest["input_profile"]
        manifest["entries"][0]["input_sha256"] = sha(canonical(source))
        (self.bundle / "manifest.json").write_text(json.dumps(manifest))
        request = json.loads((self.bundle / key / "request.json").read_text())
        request[1]["content"] = canonical(source)
        (self.bundle / key / "request.json").write_text(json.dumps(request))
        with patch("compute_bench.rewriting.core.ChatClient") as client, self.assertRaisesRegex(ValueError, "read-only"):
            generate_bundle(self.bundle, SETTINGS)
        client.assert_not_called()

    def test_generated_specs_and_delivery_are_exact_and_complete_pairs_are_not_regenerated(self):
        cases = build_coding_cases(host_task_ids=["coding-01", "coding-02"],
                                   atomic_task_ids=["rewrite-user-record", "classify-timeout-event"])
        client = generate_fixture(self.bundle, cases)
        self.assertEqual(client.return_value.complete.call_count, 4)
        docs = load_bundle(self.bundle, cases)
        for case in cases:
            self.assertIn(render_reference(case, "clean"), docs[case["id"]])
            specification = re.search(r"```json\n(.*?)\n```", docs[case["id"]], re.DOTALL)[1]
            self.assertEqual(json.loads(specification), case["crowd_task"])
            self.assertIn(public_input(case)["delivery_protocol"], docs[case["id"]])
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            generate_bundle(self.bundle, SETTINGS)
            client.assert_not_called()
        self.assertNotIn(SETTINGS.api_key, (self.bundle / "manifest.json").read_text())

    def test_parallel_generation_is_bounded_and_manifest_keeps_all_results(self):
        cases = build_coding_cases(host_task_ids=["coding-01", "coding-02"],
                                   atomic_task_ids=["rewrite-user-record", "classify-timeout-event"])
        prepare_bundle(self.bundle, cases)
        barrier = threading.Barrier(2)
        lock = threading.Lock()
        active = peak = 0

        def complete(request):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                barrier.wait(timeout=5)
                return {"content": json.dumps(ANSWER)}, {}
            finally:
                with lock:
                    active -= 1

        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.side_effect = complete
            manifest = generate_bundle(self.bundle, SETTINGS, workers=2)
            self.assertEqual(client.return_value.complete.call_count, 4)
            self.assertEqual(client.return_value.close.call_count, 4)
        self.assertEqual(peak, 2)
        self.assertTrue(all(entry["status"] == "complete" for entry in manifest["entries"]))
        self.assertEqual(json.loads((self.bundle / "manifest.json").read_text()), manifest)
        self.assertEqual(len(load_bundle(self.bundle, cases)), 4)
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            generate_bundle(self.bundle, SETTINGS, workers=4)
            client.assert_not_called()

    def test_parallel_failure_saves_inflight_success_and_stops_scheduling(self):
        cases = build_coding_cases(host_task_ids=["coding-01", "coding-02", "coding-03"],
                                   atomic_task_ids=["rewrite-user-record"])
        prepare_bundle(self.bundle, cases)
        barrier = threading.Barrier(2)
        failure_saved = threading.Event()
        first_source = public_input(cases[0])["original_reference"]
        from compute_bench.io import write_json

        def persist(path, value):
            write_json(path, value)
            if path.name == "manifest.json" and any(e["status"] == "invalid" for e in value["entries"]):
                failure_saved.set()

        def complete(request):
            barrier.wait(timeout=5)
            if json.loads(request[1]["content"])["original_reference"] == first_source:
                return {"content": "invalid JSON"}, {}
            self.assertTrue(failure_saved.wait(timeout=5))
            return {"content": json.dumps(ANSWER)}, {}

        with patch("compute_bench.rewriting.core.ChatClient") as client, \
             patch("compute_bench.rewriting.core.write_json", side_effect=persist):
            client.return_value.complete.side_effect = complete
            with self.assertRaisesRegex(ValueError, "Invalid rewrite response"):
                generate_bundle(self.bundle, SETTINGS, workers=2)
            self.assertEqual(client.return_value.complete.call_count, 2)
            self.assertEqual(client.return_value.close.call_count, 2)
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        self.assertEqual([e["status"] for e in manifest["entries"]], ["invalid", "complete", "prepared"])
        self.assertEqual(len(load_bundle(self.bundle, [cases[1]])), 1)
        self.assertFalse((self.bundle / cases[2]["id"] / "response.json").exists())

    def test_parallel_resume_reuses_saved_response_and_only_calls_missing_pair(self):
        cases = build_coding_cases(host_task_ids=["coding-01", "coding-02"],
                                   atomic_task_ids=["rewrite-user-record"])
        prepare_bundle(self.bundle, cases)
        response = {"message": {"content": json.dumps(ANSWER)}, "metadata": {}}
        (self.bundle / cases[0]["id"] / "response.json").write_text(json.dumps(response))
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = response["message"], response["metadata"]
            generate_bundle(self.bundle, SETTINGS, workers=2)
            client.return_value.complete.assert_called_once()
            client.return_value.close.assert_called_once()
        self.assertEqual(len(load_bundle(self.bundle, cases)), 2)

    def test_generate_cli_passes_workers_and_rejects_nonpositive_values_before_credentials(self):
        with patch("compute_bench.rewriting.cli.Settings.load", return_value=SETTINGS), \
             patch("compute_bench.rewriting.cli.generate_bundle", return_value={"entries": []}) as generate, \
             redirect_stdout(io.StringIO()):
            main(["rewrite", "generate", str(self.bundle), "--workers", "4"])
        generate.assert_called_once_with(self.bundle, SETTINGS, workers=4, retry_invalid=False)
        for workers in (0, -1):
            with self.subTest(workers=workers), patch("compute_bench.rewriting.cli.Settings.load") as settings:
                with self.assertRaises(SystemExit):
                    main(["rewrite", "generate", str(self.bundle), "--workers", str(workers)])
                settings.assert_not_called()
                with self.assertRaisesRegex(ValueError, "workers must be positive"):
                    generate_bundle(self.bundle, SETTINGS, workers=workers)

    def test_retry_invalid_archives_response_skips_complete_and_finishes_pending(self):
        cases = build_coding_cases(host_task_ids=["coding-01", "coding-02", "coding-03"],
                                   atomic_task_ids=["rewrite-user-record"])
        prepare_bundle(self.bundle, cases)
        valid = {"message": {"content": json.dumps(ANSWER)}, "metadata": {"usage": {"total_tokens": 7}}}
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.side_effect = [(valid["message"], valid["metadata"]),
                                                        ({"content": "bad JSON"}, {})]
            with self.assertRaisesRegex(ValueError, "Invalid rewrite response"):
                generate_bundle(self.bundle, SETTINGS)
        failed = self.bundle / cases[1]["id"]
        original = (failed / "response.json").read_bytes()
        completed = {p.name: p.read_bytes() for p in (self.bundle / cases[0]["id"]).iterdir()}
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = valid["message"], valid["metadata"]
            manifest = generate_bundle(self.bundle, SETTINGS, workers=2, retry_invalid=True)
            self.assertEqual(client.return_value.complete.call_count, 2)
        archives = list((failed / "failed_attempts").glob("*/response.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), original)
        error = json.loads(archives[0].with_name("error.json").read_text())
        self.assertEqual(error["error"], "JSONDecodeError")
        self.assertIn("error_detail", error)
        self.assertEqual(completed, {p.name: p.read_bytes() for p in (self.bundle / cases[0]["id"]).iterdir()})
        self.assertTrue(all(e["status"] == "complete" and "error_detail" not in e for e in manifest["entries"]))
        self.assertEqual(len(load_bundle(self.bundle, cases)), 3)

    def test_retry_is_bounded_and_default_resume_does_not_call_again(self):
        prepare_bundle(self.bundle, self.cases)
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = ({"content": "bad JSON"}, {})
            with self.assertRaisesRegex(ValueError, "retry-invalid"):
                generate_bundle(self.bundle, SETTINGS, retry_invalid=True)
            self.assertEqual(client.return_value.complete.call_count, 2)
        pair = self.bundle / self.case["id"]
        self.assertEqual(len(list((pair / "failed_attempts").glob("*/response.json"))), 1)
        self.assertTrue((pair / "response.json").exists())
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            with self.assertRaisesRegex(ValueError, "Invalid rewrite response"):
                generate_bundle(self.bundle, SETTINGS)
            client.assert_not_called()
        # A later explicit retry keeps previous archives and uses the same frozen request.
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = ({"content": json.dumps(ANSWER)}, {})
            generate_bundle(self.bundle, SETTINGS, retry_invalid=True)
            client.return_value.complete.assert_called_once_with(json.loads((pair / "request.json").read_text()))
        self.assertEqual(len(list((pair / "failed_attempts").glob("*/response.json"))), 2)
        self.assertEqual(len(load_bundle(self.bundle, self.cases)), 1)

    def test_interrupted_retry_keeps_archive_and_can_resume(self):
        prepare_bundle(self.bundle, self.cases)
        pair = self.bundle / self.case["id"]
        (pair / "response.json").write_text(json.dumps({"message": {"content": "bad JSON"}, "metadata": {}}))
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.side_effect = OSError("offline")
            with self.assertRaisesRegex(OSError, "offline"):
                generate_bundle(self.bundle, SETTINGS, retry_invalid=True)
            client.return_value.close.assert_called_once()
        self.assertEqual(len(list((pair / "failed_attempts").glob("*/response.json"))), 1)
        self.assertFalse((pair / "response.json").exists())
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = ({"content": json.dumps(ANSWER)}, {})
            generate_bundle(self.bundle, SETTINGS)
            client.return_value.complete.assert_called_once()
        self.assertEqual(len(load_bundle(self.bundle, self.cases)), 1)

    def test_generate_cli_enables_explicit_retry(self):
        with patch("compute_bench.rewriting.cli.Settings.load", return_value=SETTINGS), \
             patch("compute_bench.rewriting.cli.generate_bundle", return_value={"entries": []}) as generate, \
             redirect_stdout(io.StringIO()):
            main(["rewrite", "generate", str(self.bundle), "--workers", "4", "--retry-invalid"])
        generate.assert_called_once_with(self.bundle, SETTINGS, workers=4, retry_invalid=True)

    def test_invalid_missing_duplicate_and_hidden_slots_are_rejected(self):
        templates = [ANSWER["document_template"].replace(SLOTS[0], ""),
                     ANSWER["document_template"] + SLOTS[1],
                     "```\n" + ANSWER["document_template"] + "```\n",
                     "<!--\n" + ANSWER["document_template"] + "-->\n"]
        for template in templates:
            with self.subTest(template=template), self.assertRaises(ValueError):
                compile_document({**ANSWER, "document_template": template}, public_input(self.case))

    def test_invalid_response_preserves_evidence_but_cannot_run(self):
        prepare_bundle(self.bundle, self.cases)
        with patch("compute_bench.rewriting.core.ChatClient") as client:
            client.return_value.complete.return_value = ({"content": "not JSON"}, {})
            with self.assertRaisesRegex(ValueError, "Invalid rewrite response"):
                generate_bundle(self.bundle, SETTINGS)
            client.return_value.close.assert_called_once()
        self.assertTrue((self.bundle / self.case["id"] / "response.json").exists())
        with self.assertRaisesRegex(ValueError, "not complete"):
            load_bundle(self.bundle, self.cases)

    def test_bundle_rejects_incomplete_missing_mismatched_or_tampered_materials(self):
        prepare_bundle(self.bundle, self.cases)
        with self.assertRaisesRegex(ValueError, "not complete"):
            load_bundle(self.bundle, self.cases)
        shutil.rmtree(self.bundle)
        generate_fixture(self.bundle, self.cases)
        other = build_coding_cases(host_task_ids=["coding-02"], atomic_task_ids=["rewrite-user-record"])
        with self.assertRaisesRegex(ValueError, "missing selected pair"):
            load_bundle(self.bundle, other)
        changed = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])
        changed[0]["crowd_task"]["description"] += " changed"
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            load_bundle(self.bundle, changed)
        after = self.bundle / self.case["id"] / "after.md"
        after.write_text(after.read_text() + "changed")
        with self.assertRaisesRegex(ValueError, "hash/content mismatch"):
            load_bundle(self.bundle, self.cases)

    def test_prompt_edit_requires_new_bundle_and_length_control_matches_generated_document(self):
        generate_fixture(self.bundle, self.cases)
        enriched = apply_documents(self.cases, load_bundle(self.bundle, self.cases))[0]
        self.assertEqual(len(render_reference(enriched, "wrapped")), len(render_reference(enriched, "length_control")))
        for condition in ("clean", "direct"):
            self.assertEqual(render_reference(enriched, condition), render_reference(self.case, condition))
        (self.bundle / "prompt.md").write_text("changed prompt")
        with patch("compute_bench.rewriting.core.ChatClient") as client, self.assertRaisesRegex(ValueError, "prompt has changed"):
            generate_bundle(self.bundle, SETTINGS)
        client.assert_not_called()

    def test_run_dry_run_validates_bundle_without_starting_models(self):
        generate_fixture(self.bundle, self.cases)
        with patch("compute_bench.coding.cli.Settings.load") as settings, \
             patch("compute_bench.coding.runner.execute_coding") as execute, redirect_stdout(io.StringIO()) as output:
            main(["run", "--host-task-ids", "coding-01", "--atomic-task-ids", "rewrite-user-record",
                  "--rewrite-bundle", str(self.bundle), "--dry-run"])
        self.assertEqual(json.loads(output.getvalue())["planned_runs"], 8)
        settings.assert_not_called()
        execute.assert_not_called()

    def test_real_workspace_assignment_audit_and_repeats_use_frozen_materials(self):
        generate_fixture(self.bundle, self.cases)
        after = load_bundle(self.bundle, self.cases)[self.case["id"]]
        run = self.root / "run"
        seen = []

        def inspect(agent):
            expected = render_reference(agent.tools.case, agent.tools.condition, "compatibility_v3")
            seen.append(agent.tools.condition)
            self.assertEqual((agent.tools.workspace / "docs/reference.md").read_text(), expected)
            if agent.tools.condition == "wrapped":
                self.assertEqual(expected, after)
            self.assertEqual(agent.tools.reference, expected)
            self.assertFalse((agent.tools.workspace / "rationale.md").exists())

        _fixture(run, rewrite_bundle=self.bundle, conditions=["clean", "wrapped", "length_control"],
                 repeats=2, delivered=True, inspect_agent=inspect)
        self.assertEqual(len(seen), 6)
        assignments = list((run / "platform/assignments").glob("*.json"))
        self.assertEqual(len(assignments), 6)
        for path in assignments:
            assignment = json.loads(path.read_text())
            text = (Path(assignment["workspace"]) / "docs/reference.md").read_text()
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), assignment["reference_sha256"])
        shutil.rmtree(self.bundle)
        audited = audit_directory(run, regrade=True)
        self.assertTrue(audited["passed"], audited["errors"])
        copied = run / "reference_rewrite" / self.case["id"] / "after.md"
        copied.write_text(copied.read_text() + "tampered")
        self.assertFalse(audit_directory(run)["passed"])

    def test_resume_uses_run_local_materials_after_external_bundle_is_removed(self):
        generate_fixture(self.bundle, self.cases)
        after = load_bundle(self.bundle, self.cases)[self.case["id"]]
        run = self.root / "run"
        with patch("compute_bench.coding.runner.create_workspace", side_effect=OSError("synthetic bootstrap failure")):
            with self.assertRaisesRegex(RuntimeError, "failed in the harness"):
                _fixture(run, rewrite_bundle=self.bundle)
        shutil.rmtree(self.bundle)

        def agent_run(agent, task, trace):
            self.assertEqual((agent.tools.workspace / "docs/reference.md").read_text(), after)
            (agent.tools.workspace / "solution.py").write_text(agent.tools.case["reference_files"]["solution.py"])
            trace.parent.mkdir(parents=True, exist_ok=True)
            trace.write_text('{"kind":"synthetic"}\n')
            return {"status": "completed", "error": None, "final_content": "fixture",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "reasoning_tokens": 0},
                    "llm_calls": 1, "tool_calls": 0, "latency_seconds": .01,
                    "api_response_ids": ["fixture"], "trace_file": str(trace), "provider_truncated": False}

        with patch("compute_bench.coding.runner.ChatClient"), \
             patch("compute_bench.coding.runner.CodingAgent.run", autospec=True, side_effect=agent_run), \
             redirect_stdout(io.StringIO()):
            result = resume_coding(Settings(api_key="fixture", model="fixture-model"), run, workers=1)
        self.assertTrue(result["all_planned_recorded"])
        audited = audit_directory(run)
        self.assertTrue(audited["passed"], audited["errors"])


if __name__ == "__main__":
    unittest.main()
