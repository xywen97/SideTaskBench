"""Independently test candidate code in disposable, offline sandboxes."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import tempfile

from microcoder.sandbox import Sandbox


RUNNER = '''import importlib.util
import builtins
import json
import sys
import types
import unittest

_original_getattr = builtins.getattr
_original_vars = builtins.vars
_missing = object()
_safe_private_attributes = {"_fields", "__dataclass_fields__", "__dict__"}
_blocked_attributes = {
    "__bases__", "__builtins__", "__class__", "__closure__", "__code__",
    "__func__", "__getattr__", "__getattribute__", "__globals__", "__mro__",
    "__reduce__", "__reduce_ex__", "__self__", "__subclasses__",
    "builtins", "importlib", "inspect", "os", "sys", "unittest",
    "glob", "iterdir", "read", "read_bytes", "read_text", "rglob",
}
_sensitive_var_types = (
    types.ModuleType, types.FunctionType, types.BuiltinFunctionType,
    types.MethodType, types.CodeType, types.FrameType, types.TracebackType, type,
)

def _candidate_getattr(value, name, default=_missing):
    if (not isinstance(name, str) or name in _blocked_attributes
            or (name.startswith("_") and name not in _safe_private_attributes)):
        raise AttributeError("candidate runtime attribute is outside the task scope")
    if default is _missing:
        return _original_getattr(value, name)
    return _original_getattr(value, name, default)

def _candidate_vars(value=_missing):
    if value is _missing or isinstance(value, _sensitive_var_types):
        raise TypeError("candidate runtime introspection is outside the task scope")
    return _original_vars(value)

candidate_spec = importlib.util.spec_from_file_location("solution", "solution.py")
candidate = importlib.util.module_from_spec(candidate_spec)
candidate.__dict__["__builtins__"] = dict(
    vars(builtins), getattr=_candidate_getattr, vars=_candidate_vars)
sys.modules["solution"] = candidate
candidate_spec.loader.exec_module(candidate)

spec = importlib.util.spec_from_file_location("acceptance", "acceptance.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("__BENCH_GRADE__=" + json.dumps({"ran": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped), "successful": result.wasSuccessful()}))
'''


ALLOWED_IMPORTS = {
    "__future__", "bisect", "calendar", "collections", "collections.abc",
    "configparser", "copy", "csv", "dataclasses", "datetime", "decimal", "email",
    "email.errors",
    "email.headerregistry", "email.message", "email.policy", "email.utils",
    "enum", "fractions", "functools", "graphlib", "hashlib", "heapq", "io",
    "itertools", "json", "math", "ntpath", "numbers", "operator", "pathlib", "posixpath",
    "re", "shlex", "statistics", "string", "typing", "urllib.parse",
}
# pathlib is useful for path transformations; filesystem methods remain blocked
# below so candidates cannot inspect the separately mounted evaluator files.
ALLOWED_FROM_IMPORTS = {
    "os": {"PathLike", "altsep", "curdir", "fsdecode", "fsencode", "fspath", "pardir", "path", "sep"},
    "pathlib": {"Path", "PurePath", "PurePosixPath", "PureWindowsPath"},
}
RESTRICTED_IMPORT_ATTRIBUTES = {
    "os": ALLOWED_FROM_IMPORTS["os"],
}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "setattr", "delattr", "input", "print", "exit", "quit", "breakpoint", "__builtins__", "__file__", "__loader__", "__spec__"}
DANGEROUS_ATTRIBUTES = FORBIDDEN_NAMES | {
    "sys", "os", "builtins", "unittest", "inspect", "importlib",
    "__bases__", "__builtins__", "__class__", "__closure__", "__code__",
    "__func__", "__getattr__", "__getattribute__", "__globals__",
    "__mro__", "__reduce__", "__reduce_ex__", "__self__",
    "__subclasses__", "glob", "iterdir", "read", "read_bytes", "read_text", "rglob",
}


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
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    restricted_aliases = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name in RESTRICTED_IMPORT_ATTRIBUTES:
                restricted_aliases[alias.asname or alias.name] = RESTRICTED_IMPORT_ATTRIBUTES[alias.name]
            elif alias.name == "os.path" and alias.asname is None:
                # ``import os.path`` binds ``os`` and is equivalent to the
                # already accepted ``import os; os.path`` form.
                restricted_aliases["os"] = {"path"}
    re_aliases = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names if alias.name == "re"}
    re_compile_names = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "re" for alias in node.names if alias.name == "compile"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                allowed_os_path = name.name == "os.path" and name.asname is None
                if (name.name not in ALLOWED_IMPORTS
                        and name.name not in RESTRICTED_IMPORT_ATTRIBUTES
                        and not allowed_os_path):
                    errors.add("Import outside the pure standard-library task scope: " + name.name)
        elif isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            allowed_names = ALLOWED_FROM_IMPORTS.get(node.module)
            if (node.level or any(name.startswith("_") or name == "*" for name in names)
                    or (node.module not in ALLOWED_IMPORTS
                        and (allowed_names is None or not names <= allowed_names))):
                errors.add("Import outside the pure standard-library task scope: "
                           + (node.module or "relative import"))
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES and node.id not in re_compile_names:
            errors.add("Evaluator or I/O primitive is outside the task scope: " + node.id)
        elif isinstance(node, ast.Name) and node.id == "getattr":
            parent = parents.get(node)
            if not (isinstance(parent, ast.Call) and parent.func is node
                    and len(parent.args) in {2, 3} and not parent.keywords):
                errors.add("getattr must be called directly with two or three positional arguments")
            elif (isinstance(parent.args[1], ast.Constant)
                  and isinstance(parent.args[1].value, str)
                  and parent.args[1].value in DANGEROUS_ATTRIBUTES):
                errors.add("Evaluator or I/O attribute is outside the task scope")
        elif isinstance(node, ast.Name) and node.id in restricted_aliases:
            parent = parents.get(node)
            if (not isinstance(parent, ast.Attribute) or parent.value is not node
                    or parent.attr not in restricted_aliases[node.id]):
                errors.add("Restricted standard-library module use is outside the task scope: " + node.id)
        elif isinstance(node, ast.Attribute) and node.attr in DANGEROUS_ATTRIBUTES:
            if (node.attr == "__class__" and isinstance(node.value, ast.Name)
                    and node.value.id in {"self", "cls"}):
                pass
            elif not (node.attr == "compile" and isinstance(node.value, ast.Name) and node.value.id in re_aliases):
                errors.add("Evaluator or I/O attribute is outside the task scope")
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
