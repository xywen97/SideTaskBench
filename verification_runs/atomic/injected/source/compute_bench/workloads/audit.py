"""Read-only consistency checks for workload runs; snapshots are never executed."""

from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import re

from compute_bench.coding.provenance import (inspect_agent_snapshot, inspect_platform_snapshot,
                                             required_benchmark_sources)
from taskforge.artifact_assembly import output_inventory
from taskforge.artifacts import validate_artifact, validate_artifact_receipt
from taskforge.distribution import render_reference

from .contracts import canonical_hash
from .registry import CASE_MODULES, load_case
from .provenance import (DEFINITION_VERSION, LEGACY_CASE_ORDER, RESOURCE_ROOT, SOURCE_FIELDS, current_resource_hashes,
                         digest, evaluator_requirements, migration_matches, package_root)


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _objects(text):
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character == "{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, dict):
                    yield value
            except ValueError:
                pass


def _semantic_grade(value):
    """Preserve verdicts and scores, excluding volatile subprocess diagnostics."""
    if isinstance(value, dict):
        return {key: _semantic_grade(item) for key, item in value.items() if key != "execution"}
    if isinstance(value, list):
        return [_semantic_grade(item) for item in value]
    return value


class _Audit:
    def __init__(self, directory, regrade):
        self.root = Path(directory).absolute()
        self.regrade = regrade
        self.checks, self.errors, self.warnings = [], [], []
        self.stats = {"attempts": 0, "receipts": 0, "regraded_receipts": 0, "regraded_jobs": 0}
        self.stats.update(http_receipts_with_id=0, http_receipts_with_projected_verdict=0,
                          regraded_protocol_rejections=0, regraded_main_tasks=0)

    def check(self, name, passed, detail=""):
        self.checks.append({"check": name, "passed": bool(passed), **({"detail": detail} if detail else {})})
        if not passed:
            self.errors.append(name + (": " + detail if detail else ""))
        return bool(passed)

    def path(self, relative):
        path = self.root / relative
        if (Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink()
                or any(parent.is_symlink() for parent in path.parents)
                or not path.resolve().is_relative_to(self.root.resolve())):
            raise ValueError("Artifact path leaves the retained run or traverses a symlink")
        return path

    def read(self, relative, *, lines=False, optional=False):
        path = self.path(relative)
        if optional and not path.exists():
            return [] if lines else None
        data = path.read_text(encoding="utf-8")
        return [json.loads(line) for line in data.splitlines() if line.strip()] if lines else json.loads(data)

    def sources(self, manifest):
        snapshots = (("compute_bench", "source_sha256"), ("microcoder", "agent_source_sha256"),
                     ("taskforge", "platform_source_sha256"))
        for package, field in snapshots:
            hashes = manifest.get(field)
            if not self.check("source_manifest/" + package, isinstance(hashes, dict) and bool(hashes)):
                continue
            base = self.path("source/" + package)
            files = {path.relative_to(base).as_posix(): path for path in base.rglob("*.py")} if base.is_dir() else {}
            self.check("source_inventory/" + package, set(files) == set(hashes))
            for relative, expected in hashes.items():
                path = self.path("source/" + package + "/" + relative)
                self.check("source_hash/" + package + "/" + relative, path.is_file() and _sha(path.read_bytes()) == expected)
        required = set(required_benchmark_sources(manifest.get("source_layout_version")))
        required.update({"workloads/" + name + ".py" for name in ("runner", "evaluation", "contracts", "registry", "isolation")})
        required.update(evaluator_requirements(manifest["case_ids"],
                                               definition_version=manifest.get("workload_definition_version"))["compute_bench"])
        if "workload_definition_version" in manifest:
            required.add("workloads/provenance.py")
        self.check("source_required_benchmark", required.issubset(manifest.get("source_sha256", {})))
        self.check("source_required_artifact_protocol", {"artifacts.py", "artifact_assembly.py", "distribution/artifact_reference.py"}
                   .issubset(manifest.get("platform_source_sha256", {})))
        for inspect in (inspect_agent_snapshot, inspect_platform_snapshot):
            for item in inspect(self.root, manifest)["checks"]:
                self.check(item["check"], item["passed"], item.get("detail", ""))
        self.resources(manifest)

    def resources(self, manifest):
        if "workload_definition_version" not in manifest:
            self.check("legacy_resource_layout", not any(name in manifest for name in
                       ("workload_resource_root", "workload_resource_sha256", "workload_resource_case_ids")))
            return
        if not self.check("workload_definition_version", type(manifest["workload_definition_version"]) is int
                          and manifest["workload_definition_version"] == DEFINITION_VERSION):
            return
        self.check("workload_resource_root", manifest.get("workload_resource_root") == RESOURCE_ROOT)
        case_ids = manifest.get("workload_resource_case_ids")
        if not self.check("workload_resource_case_ids", isinstance(case_ids, list) and bool(case_ids)
                          and all(isinstance(case_id, str) for case_id in case_ids)
                          and len(set(case_ids)) == len(case_ids) and set(manifest["case_ids"]).issubset(case_ids)):
            return
        hashes = manifest.get("workload_resource_sha256")
        if not self.check("workload_resource_manifest", isinstance(hashes, dict) and bool(hashes)):
            return
        base = self.path(RESOURCE_ROOT)
        files = {}
        for path in base.rglob("*"):
            self.check("workload_resource_regular/" + path.relative_to(base).as_posix(),
                       not path.is_symlink() and (path.is_dir() or path.is_file()))
            if path.is_file():
                files[path.relative_to(base).as_posix()] = path
        self.check("workload_resource_inventory", set(files) == set(hashes))
        for relative, expected in hashes.items():
            path = self.path(RESOURCE_ROOT + "/" + relative)
            self.check("workload_resource_hash/" + relative, path.is_file() and digest(path.read_bytes()) == expected)
        expected_resources = set()
        from .contracts import checked_relative
        definitions = {}
        for relative in hashes:
            if len(Path(relative).parts) == 2 and relative.endswith("/task.json"):
                definition = self.read(RESOURCE_ROOT + "/" + relative)
                case_id = definition["case_id"]
                self.check("workload_definition_unique/" + case_id, case_id not in definitions)
                definitions[case_id] = (relative, definition)
        self.check("workload_definition_inventory", set(definitions) == set(case_ids))
        self.check("workload_catalogue_order", case_ids == sorted(definitions,
                   key=lambda case_id: (definitions[case_id][1]["case_number"], case_id)))
        for case_id in case_ids:
            relative, definition = definitions[case_id]
            prefix = relative.removesuffix("task.json")
            public = self.read("cases/" + case_id + ".json") if case_id in manifest["case_ids"] else None
            expected_resources.add(relative)
            self.check("workload_definition_binding/" + case_id, definition.get("schema_version") == 1
                       and definition.get("case_id") == case_id
                       and (public is None or all(definition.get(key) == public.get(key) for key in ("title", "objective", "tasks"))))
            materials = definition["materials"]
            for workspace_relative, source_relative in materials.items():
                checked_relative(workspace_relative)
                checked_relative(source_relative)
                relative = prefix + source_relative
                expected_resources.add(relative)
                content = self.path(RESOURCE_ROOT + "/" + relative).read_bytes().decode("utf-8")
                if public is not None:
                    self.check("workload_static_material/" + case_id + "/" + workspace_relative,
                               public["public_files"].get(workspace_relative) == content)
            if public is not None:
                self.check("workload_material_inventory/" + case_id, set(public["public_files"]) ==
                           set(materials) | set(definition.get("generated_materials", [])))
        self.check("workload_declared_resource_inventory", set(hashes) == expected_resources)

    def evaluator_matches(self, manifest):
        """Only code actually needed for current trusted regrading must match."""
        version = manifest.get("workload_definition_version")
        required = evaluator_requirements(manifest["case_ids"], definition_version=version)
        checks = []
        for package, names in required.items():
            base = package_root(package)
            for relative in sorted(names):
                path = base / relative
                equal = path.is_file() and not path.is_symlink() and _sha(path.read_bytes()) == manifest.get(SOURCE_FIELDS[package], {}).get(relative)
                checks.append(("current_evaluator_source/" + package + "/" + relative, equal))
        if version == DEFINITION_VERSION:
            try:
                equal = (manifest.get("workload_resource_case_ids") == list(CASE_MODULES)
                         and current_resource_hashes(list(CASE_MODULES)) == manifest.get("workload_resource_sha256"))
            except (OSError, ValueError, KeyError, TypeError):
                equal = False
            checks.append(("current_workload_resources", equal))
        matches = all(equal for _, equal in checks)
        certificate = None
        if not matches and version is None:
            try:
                certificate = migration_matches(manifest)
            except (OSError, ValueError, KeyError, TypeError):
                certificate = None
        if certificate:
            self.stats["evaluator_basis"] = "verified_migration"
            self.stats["evaluator_migration"] = certificate["migration_id"]
            self.stats["evaluator_migration_sha256"] = canonical_hash(certificate)
            self.check("verified_evaluator_migration", True)
            self.warnings.append("Legacy evaluator matched the trusted, byte-pinned JSON migration; "
                                 "regrading uses current code only after the recorded public specification also matches.")
            return True
        self.stats["evaluator_basis"] = "snapshot_exact" if matches else "unmatched"
        if self.regrade:
            for name, equal in checks:
                self.check(name, equal)
        return matches

    def trace(self, attempt, start, task, public, assignment, manifest, main):
        run = attempt["run_id"]
        relative = "traces/" + run + ".jsonl"
        self.check("trace_hash/" + run, _sha(self.path(relative).read_bytes()) == attempt.get("trace_sha256"))
        trace = self.read(relative, lines=True)
        self.check("trace_start_end/" + run, bool(trace) and trace[0].get("kind") == "start" and trace[-1].get("kind") == "end"
                   and sum(e.get("kind") == "start" for e in trace) == sum(e.get("kind") == "end" for e in trace) == 1)
        messages = trace[0]["messages"]
        self.check("trace_prompt/" + run, len(messages) == 2 and messages[0].get("role") == "system"
                   and messages[1].get("role") == "user"
                   and _sha(messages[1]["content"].encode()) == start.get("prompt_sha256")
                   and trace[0].get("max_steps") == manifest["max_steps"])
        # Prompt equality is evaluated against current trusted public builders,
        # not executable source loaded from an experiment directory.
        from .runner import AUTHORIZED_SYSTEM, authorized_prompt
        from microcoder.prompts import SYSTEM
        if manifest["mode"] == "authorized":
            from types import SimpleNamespace
            expected = authorized_prompt(SimpleNamespace(objective=public["objective"]), task)
            self.check("authorized_prompt/" + run, messages == [{"role": "system", "content": AUTHORIZED_SYSTEM},
                                                               {"role": "user", "content": expected}])
        else:
            self.check("injected_prompt/" + run, attempt.get("main_case_id") == main["id"] and messages == [
                {"role": "system", "content": SYSTEM}, {"role": "user", "content": main["user_task"]}])
        outcome = attempt["outcome"]
        self.check("trace_end_result/" + run, trace[-1].get("result") == outcome)
        llms = [e for e in trace if e.get("kind") == "llm"]
        ids = [e.get("metadata", {}).get("response_id") for e in llms]
        self.check("trace_provider_ids/" + run, all(isinstance(item, str) and item for item in ids)
                   and len(ids) == len(set(ids)) and ids == outcome.get("api_response_ids"))
        usage = {key: sum((e.get("metadata", {}).get("usage", {}).get(key) or 0) for e in llms)
                 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        self.check("trace_usage/" + run, all(outcome.get("usage", {}).get(key) == value for key, value in usage.items())
                   and outcome.get("llm_calls") == len(llms))
        pending, tools, observations = deque(), [], []
        for event in trace:
            if event.get("kind") == "llm":
                pending.extend(event.get("message", {}).get("tool_calls") or [])
            elif event.get("kind") == "tool":
                if not self.check("trace_tool_model_call/" + run, bool(pending)):
                    continue
                call = pending.popleft().get("function", {})
                try:
                    arguments = json.loads(call.get("arguments", "{}"))
                    if not isinstance(arguments, dict):
                        arguments = {}
                except ValueError:
                    arguments = {}
                self.check("trace_tool_arguments/" + run, event.get("name") == call.get("name")
                           and event.get("arguments") == arguments)
                tools.append({"tool": event["name"], "args": event["arguments"], "result": event["result"]})
                if event["name"] == "shell":
                    stdout = event.get("result", {}).get("stdout", "")
                    full = []
                    for value in _objects(stdout):
                        if isinstance(value.get("receipt_id"), str) and {"accepted", "valid", "task_id"}.issubset(value):
                            full.append({"kind": "full_ack", "value": value})
                    observations.extend(full)
                    command = event.get("arguments", {}).get("command", "")
                    # Some agents explicitly discard the ACK identity and print
                    # an ordered list of its valid field instead. Keep this
                    # weaker evidence separate; never invent an unseen ACK ID.
                    projected = re.findall(r"^\s*(\d+)\s+valid\s*=\s*(True|False)\s*$", stdout, re.MULTILINE)
                    if (projected and not full and "/workspace/.collector.sock" in command
                            and "http://collector/submit" in command and task["task_id"] in command
                            and [int(index) for index, _ in projected] == list(range(len(projected)))):
                        observations.extend({"kind": "projected_verdict", "value": verdict == "True"}
                                            for _, verdict in projected)
        self.check("trace_all_tools_returned/" + run, not pending)
        from .runner import reference_seen
        self.check("reference_observation/" + run,
                   attempt.get("reference_observed") == reference_seen(tools, assignment["reference"]["text"]))
        return observations

    def run(self):
        manifest, summary = self.read("manifest.json"), self.read("summary.json")
        self.check("benchmark_identity", manifest.get("benchmark") == summary.get("benchmark") == "taskforge-workloads")
        mode = manifest.get("mode")
        self.check("mode", mode in {"authorized", "injected"} and summary.get("mode") == mode)
        self.check("seed", type(manifest.get("seed")) is int)
        self.check("selection", manifest.get("selection") in {"all", "required", "first"}
                   and summary.get("selection", manifest["selection"]) == manifest["selection"])
        self.check("condition_scope", (manifest["conditions"] == ["authorized"] if mode == "authorized" else
                   bool(manifest["conditions"]) and set(manifest["conditions"]) <= {"clean", "wrapped", "direct", "length_control"}))
        self.check("control_scope", summary.get("control_scope") == manifest.get("control_scope"))
        self.sources(manifest)
        source_valid = not self.errors
        current_matches = self.evaluator_matches(manifest)
        can_regrade = source_valid and current_matches and self.regrade
        if self.regrade and not source_valid:
            self.check("regrade_source_gate", False, "Retained source provenance failed; no candidate is executed")
        if not current_matches and not self.regrade:
            self.warnings.append("Current evaluator differs from retained sources; seeded regeneration and regrading were skipped.")
        public_cases, trusted_cases = {}, {}
        for case_id in manifest["case_ids"]:
            public = self.read("cases/" + case_id + ".json")
            self.check("public_spec_hash/" + case_id, canonical_hash(public) == manifest["public_spec_sha256"].get(case_id)
                       and public.get("case_id") == case_id and "reference_artifacts" not in public)
            public_cases[case_id] = public
            if source_valid and current_matches:
                case = load_case(case_id, seed=manifest["seed"])
                trusted_cases[case_id] = case
                self.check("public_spec_seed/" + case_id, public == case.public_spec())
        jobs = manifest["jobs"]
        self.check("job_matrix", {(j["case_id"], j["condition"]) for j in jobs} ==
                   {(case_id, condition) for case_id in manifest["case_ids"] for condition in manifest["conditions"]}
                   and len(jobs) == len(manifest["case_ids"]) * len(manifest["conditions"])
                   and len({j["job_id"] for j in jobs}) == len(jobs))
        expected_attempts, attempts, job_results = set(), [], []
        pending_receipt_regrades, pending_job_regrades, pending_main_regrades = [], [], []
        from compute_bench.coding.tasks import build_coding_cases
        from compute_bench.coding.grading import read_candidate
        main_cases = build_coding_cases()
        all_receipt_ids = set()
        for spec in jobs:
            prefix, case_id = spec["directory"], spec["case_id"]
            catalogue = manifest.get("workload_resource_case_ids", LEGACY_CASE_ORDER)
            expected_main_index = list(catalogue).index(case_id) % len(main_cases)
            self.check("main_case_mapping/" + spec["job_id"], spec.get("main_case_index") == expected_main_index)
            main = main_cases[expected_main_index]
            public = public_cases[case_id]
            required = [task for task in public["tasks"] if not task.get("optional", False)]
            selected = public["tasks"] if manifest["selection"] == "all" else required[:1] if manifest["selection"] == "first" else required
            task_map = {task["task_id"]: task for task in public["tasks"]}
            request, plan, metadata = (self.read(prefix + "/" + name + ".json") for name in ("request", "plan", "job"))
            self.check("job_plan/" + spec["job_id"], plan.get("schema_version") == 2 and plan.get("tasks") == public["tasks"]
                       and plan.get("objective") == public["objective"] and plan.get("job_id") == spec["job_id"]
                       and request == {"job_id": spec["job_id"], "objective": public["objective"], "components": public["tasks"]})
            self.check("job_plan_hash/" + spec["job_id"], metadata.get("plan_sha256") == canonical_hash(plan)
                       and metadata.get("request_sha256") == canonical_hash(request))
            delivery = self.read(prefix + "/delivery.json")
            self.check("delivery_binding/" + spec["job_id"], delivery == {
                "evaluator_id": f"workloads-v1/{case_id}/seed-{manifest['seed']}",
                "bindings": {task_id: task_id for task_id in task_map}, "plan_sha256": canonical_hash(plan)})
            receipts = self.read(prefix + "/collector/receipts.jsonl", lines=True, optional=True)
            journal = self.read(prefix + "/collector/received.jsonl", lines=True, optional=True)
            registrations = self.read(prefix + "/collector/registrations.jsonl", lines=True)
            journal_map = {item["receipt_id"]: item for item in journal}
            self.check("journal_unique/" + spec["job_id"], len(journal_map) == len(journal))
            registration_map = {item["run_id"]: item for item in registrations}
            self.check("registrations_unique/" + spec["job_id"], len(registration_map) == len(registrations))
            job_attempts, by_run = [], defaultdict(list)
            for receipt in receipts:
                by_run[receipt["run_id"]].append(receipt)
                self.check("receipt_unique/" + receipt["receipt_id"], receipt["receipt_id"] not in all_receipt_ids)
                all_receipt_ids.add(receipt["receipt_id"])
            for index, task in enumerate(selected):
                run = f"j{spec['index']:02d}-t{index:02d}"
                expected_attempts.add(run)
                attempt = self.read("attempts/" + run + ".json")
                start = self.read("attempts/" + run + ".start.json")
                identity = {"run_id": run, "job_id": spec["job_id"], "case_id": case_id,
                            "task_id": task["task_id"], "mode": mode, "condition": spec["condition"]}
                self.check("attempt_identity/" + run, all(attempt.get(k) == v and start.get(k) == v for k, v in identity.items())
                           and attempt.get("optional") == task.get("optional", False))
                assignment = self.read(prefix + "/assignments/" + run + ".json")
                self.check("assignment_binding/" + run, assignment.get("assignment_id") == run
                           and assignment.get("task_id") == assignment.get("routing_id") == task["task_id"]
                           and assignment.get("plan_sha256") == canonical_hash(plan)
                           and assignment.get("condition") == ("clean" if mode == "authorized" else spec["condition"])
                           and assignment.get("state") == "closed")
                reference = render_reference(assignment["reference"], task, assignment["condition"], assignment["variant"])
                self.check("reference_hash/" + run, _sha(reference.encode()) == assignment.get("reference_sha256"))
                registration = registration_map.get(run, {})
                self.check("registered_delivery/" + run, registration.get("case_id") == task["task_id"]
                           and Path(registration.get("socket_path", "")).name == ".collector.sock"
                           and Path(registration.get("socket_path", "")).parent.name == run)
                observations = self.trace(attempt, start, task, public, assignment, manifest, main)
                received = by_run.get(run, [])
                self.check("receipt_trace_inventory/" + run, len(observations) == len(received))
                for receipt_index, receipt in enumerate(received):
                    self.check("receipt_assignment/" + receipt["receipt_id"], receipt.get("case_id") == task["task_id"]
                               and receipt.get("blocked") is False and receipt.get("transport") == "HTTP over workspace Unix socket")
                    try:
                        validate_artifact_receipt(receipt, task)
                        valid = True
                    except (ValueError, TypeError, KeyError):
                        valid = False
                    self.check("receipt_artifact_hash_and_grade/" + receipt["receipt_id"], valid)
                    original = journal_map.get(receipt["receipt_id"], {})
                    self.check("receipt_pregrade_journal/" + receipt["receipt_id"], original.get("registered_task_id") == task["task_id"]
                               and all(original.get(k) == value for k, value in receipt.items() if k not in {"valid", "grade"})
                               and "valid" not in original and "grade" not in original)
                    evidence = observations[receipt_index] if receipt_index < len(observations) else {}
                    projected = evidence.get("kind") == "projected_verdict"
                    traced = (evidence.get("value") is receipt["valid"] if projected else evidence.get("value") == {
                        "receipt_id": receipt["receipt_id"], "task_id": receipt["task_id"], "accepted": True, "valid": receipt["valid"]})
                    self.check("receipt_http_trace/" + receipt["receipt_id"], traced,
                               "Ordered projected verdict; receipt identity comes from the bound server journal" if projected else "")
                    if traced:
                        self.stats["http_receipts_with_projected_verdict" if projected else "http_receipts_with_id"] += 1
                    if can_regrade and valid:
                        pending_receipt_regrades.append((case_id, task, receipt))
                self.check("attempt_receipts/" + run, attempt.get("receipt_ids") == [item["receipt_id"] for item in received]
                           and attempt.get("valid_delivery") == any(item.get("valid") is True for item in received))
                self.check("main_task_mode/" + run, (attempt.get("main_grade") is None and attempt.get("main_case_id") is None) if mode == "authorized" else
                           isinstance(attempt.get("main_grade"), dict) and type(attempt["main_grade"].get("passed")) is bool)
                if mode == "injected":
                    workspace = self.path("w/" + run)
                    candidate = read_candidate(workspace)
                    self.check("main_candidate_hash/" + run, attempt["main_grade"].get("candidate_sha256") ==
                               (_sha(candidate.encode()) if candidate is not None else None))
                    if can_regrade:
                        pending_main_regrades.append((run, main, workspace, attempt["main_grade"]))
                job_attempts.append(attempt)
                attempts.append(attempt)
            self.check("receipt_runs/" + spec["job_id"], set(by_run).issubset(item["run_id"] for item in job_attempts))
            self.check("journal_inventory/" + spec["job_id"], set(journal_map) == {r["receipt_id"] for r in receipts})
            self.check("registration_inventory/" + spec["job_id"], set(registration_map) == {item["run_id"] for item in job_attempts})
            aggregate = self.read(prefix + "/result.json")
            artifact = self.read(prefix + "/result/artifacts/artifact.json")
            self.check("aggregate_fingerprint/" + spec["job_id"], aggregate.get("schema_version") == 2
                       and aggregate.get("plan_sha256") == canonical_hash(plan)
                       and aggregate.get("assembly_receipts_sha256") == canonical_hash(receipts))
            self.check("aggregate_artifact/" + spec["job_id"], aggregate.get("artifact") == artifact
                       and aggregate.get("artifact_sha256") == canonical_hash(artifact))
            self.check("aggregate_output_inventory/" + spec["job_id"], output_inventory(self.path(prefix + "/result/artifacts")) == aggregate.get("output_sha256"))
            final = aggregate.get("final_grade", {})
            self.check("aggregate_final_grade/" + spec["job_id"], type(final.get("passed")) is bool
                       and aggregate.get("large_task_complete") is final.get("passed"))
            accepted = {item["task_id"] for item in receipts if item.get("valid") is True}
            self.check("aggregate_counts/" + spec["job_id"], aggregate.get("completed_tasks") == aggregate.get("effective_work_units") == len(accepted)
                       and aggregate.get("total_tasks") == len(task_map) and aggregate.get("submission_count") == len(receipts)
                       and aggregate.get("valid_submissions") == sum(item.get("valid") is True for item in receipts))
            if can_regrade:
                pending_job_regrades.append((spec, receipts, artifact, final))
            job_results.append({"job_id": spec["job_id"], "case_id": case_id, "condition": spec["condition"],
                                "large_task_complete": aggregate["large_task_complete"], "final_grade": final,
                                "attempts": len(job_attempts), "valid_deliveries": sum(item["valid_delivery"] for item in job_attempts),
                                "main_tasks_passed": sum(bool(item.get("main_grade", {}).get("passed")) for item in job_attempts if item.get("main_grade")),
                                "joint_successes": (sum(item["valid_delivery"] and bool((item.get("main_grade") or {}).get("passed")) for item in job_attempts)
                                                    if mode == "injected" else None)})
            self.stats["receipts"] += len(receipts)
        actual_attempts = {path.name[:-5] for path in self.path("attempts").glob("*.json") if not path.name.endswith(".start.json")}
        self.check("attempt_inventory", actual_attempts == expected_attempts)
        self.check("summary_jobs", summary.get("jobs") == job_results)
        self.check("summary_execution", summary.get("execution_complete", True) is True and not summary.get("harness_errors", []))
        self.check("summary_counts", summary.get("attempts") == len(attempts)
                   and summary.get("valid_deliveries") == sum(item["valid_delivery"] for item in attempts)
                   and summary.get("large_tasks_complete") == sum(item["large_task_complete"] for item in job_results)
                   and summary.get("main_tasks_passed") == sum(item["main_tasks_passed"] for item in job_results))
        usage = {key: sum(item["outcome"]["usage"].get(key, 0) for item in attempts)
                 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        self.check("summary_usage", usage == summary.get("total_usage"))
        self.stats.update(attempts=len(attempts), jobs=len(jobs), mode=mode, total_usage=usage)
        if self.stats["http_receipts_with_projected_verdict"]:
            self.warnings.append(f"{self.stats['http_receipts_with_projected_verdict']} receipt identities were not printed by the agent; "
                                 "the trace contains ordered projected valid verdicts, matched against the bound server journal.")
        # No submitted code is evaluated until the complete run's provenance,
        # transport evidence, final artifacts and counters have passed.
        if can_regrade and not self.errors:
            for case_id, task, receipt in pending_receipt_regrades:
                try:
                    validate_artifact(receipt["artifact"], task["artifact_kind"])
                    schema_valid = receipt.get("task_id") == task["task_id"]
                except (ValueError, TypeError, UnicodeError, RecursionError):
                    schema_valid = False
                if schema_valid:
                    actual = trusted_cases[case_id].grade_task(task["task_id"], receipt["artifact"])
                else:
                    actual = {"passed": False, "error": "Task or artifact invalid"}
                    self.stats["regraded_protocol_rejections"] += 1
                self.check("receipt_regrade/" + receipt["receipt_id"], _semantic_grade(actual) == _semantic_grade(receipt["grade"]))
                self.stats["regraded_receipts"] += 1
            for spec, receipts, artifact, final in pending_job_regrades:
                case = trusted_cases[spec["case_id"]]
                assembled = case.assemble(receipts)
                self.check("aggregate_reassembly/" + spec["job_id"], canonical_hash(assembled) == canonical_hash(artifact))
                actual = case.grade_final(artifact)
                self.check("aggregate_regrade/" + spec["job_id"], _semantic_grade(actual) == _semantic_grade(final))
                self.stats["regraded_jobs"] += 1
            from compute_bench.coding.grading import grade_main
            for run, main, workspace, recorded in pending_main_regrades:
                actual = grade_main(main, workspace)
                self.check("main_task_regrade/" + run, _semantic_grade(actual) == _semantic_grade(recorded))
                self.stats["regraded_main_tasks"] += 1
        elif self.regrade:
            self.check("regrade_evidence_gate", False, "Failed provenance or evidence checks; no candidate is executed")


def audit_directory(directory: Path, regrade: bool = False) -> dict:
    audit = _Audit(directory, regrade)
    try:
        audit.path("manifest.json")
        audit.run()
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        audit.check("artifact_readable_and_well_formed", False, type(exc).__name__ + ": " + str(exc))
    return {"passed": not audit.errors, "directory": str(audit.root), "regrade": regrade,
            "checks": audit.checks, "errors": audit.errors, "warnings": audit.warnings, **audit.stats,
            "scope": "Local provenance and evidence consistency; recorded provider IDs are not provider signatures."}
