"""Independently test candidate code in disposable, offline sandboxes."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import tempfile

from microcoder.sandbox import Sandbox


RUNNER = '''import importlib.util
import json
import unittest
spec = importlib.util.spec_from_file_location("acceptance", "acceptance.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("__BENCH_GRADE__=" + json.dumps({"ran": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped), "successful": result.wasSuccessful()}))
'''


ALLOWED_IMPORTS = {"__future__", "csv", "io", "json", "urllib.parse", "collections", "collections.abc", "datetime", "email.utils", "re", "shlex", "heapq", "math", "functools", "itertools", "typing", "decimal", "fractions", "bisect", "operator", "enum", "dataclasses", "string", "calendar"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr", "input", "print", "exit", "quit", "breakpoint", "__builtins__", "__file__", "__loader__", "__spec__"}


def source_policy(source_code: str) -> list[str]:
    """Pure-utility acceptance policy, including obvious evaluator interference.

    Runtime isolation is the security boundary; this AST check narrows candidate
    behavior for pure Python utility tasks. It is not a universal Python verifier.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ["Source is not valid Python"]
    errors = set()
    re_aliases = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names if alias.name == "re"}
    re_compile_names = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "re" for alias in node.names if alias.name == "compile"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name not in ALLOWED_IMPORTS:
                    errors.add("Import outside the pure standard-library task scope: " + name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS or any(alias.name.startswith("_") or alias.name == "*" for alias in node.names):
                errors.add("Import outside the pure standard-library task scope")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES and node.id not in re_compile_names:
            errors.add("Evaluator or I/O primitive is outside the task scope: " + node.id)
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES | {"sys", "os", "builtins", "unittest", "inspect", "importlib"}:
            if not (node.attr == "compile" and isinstance(node.value, ast.Name) and node.value.id in re_aliases):
                errors.add("Evaluator or I/O attribute is outside the task scope")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_") and node.attr != "__name__":
            # Own instance fields (_cache etc.) are ordinary implementation details.
            if not isinstance(node.value, ast.Name) or node.value.id not in {"self", "cls"}:
                errors.add("Private runtime introspection is outside the task scope")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "__BENCH_GRADE__" in node.value:
            errors.add("Evaluator marker is not candidate output")
    return sorted(errors)


def grade_source(source_code: str, test_code: str, *, timeout: float = 30) -> dict:
    if not isinstance(source_code, str) or len(source_code.encode()) > 1024 * 1024:
        return {"passed": False, "error": "Source must be text of at most 1 MiB", "tests_run": 0}
    source_hash = hashlib.sha256(source_code.encode()).hexdigest()
    policy_errors = source_policy(source_code)
    if policy_errors:
        return {"passed": False, "tests_run": 0, "source_sha256": source_hash, "policy_errors": policy_errors}
    expected_count = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") for node in ast.walk(ast.parse(test_code)))
    with tempfile.TemporaryDirectory(prefix="coding-grade-") as temporary:
        workspace = Path(temporary)
        (workspace / "solution.py").write_text(source_code, encoding="utf-8")
        (workspace / "acceptance.py").write_text(test_code, encoding="utf-8")
        (workspace / "runner.py").write_text(RUNNER, encoding="utf-8")
        result = Sandbox(workspace, allow_ipc=False).run("python3 runner.py", timeout=timeout)
    markers = [line.partition("=")[2] for line in result["stdout"].splitlines() if line.startswith("__BENCH_GRADE__=")]
    verdict = {}
    if len(markers) == 1:
        try:
            verdict = json.loads(markers[0])
        except ValueError:
            pass
    passed = (result["exit_code"] == 0 and not result["timed_out"] and expected_count > 0
              and verdict.get("ran") == expected_count and verdict.get("successful") is True
              and verdict.get("failures") == verdict.get("errors") == verdict.get("skipped") == 0)
    return {"passed": passed, "tests_run": verdict.get("ran", 0), "expected_tests": expected_count,
            "source_sha256": source_hash, "verdict": verdict, "execution": result}
