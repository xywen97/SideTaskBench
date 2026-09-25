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
