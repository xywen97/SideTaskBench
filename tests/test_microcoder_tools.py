"""MicroCoder's generic tools preserve established permissions and tool output."""

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.documents import render_reference
from compute_bench.coding.environment import CodingEnvironment, TOOLS as COMPAT_TOOLS
from compute_bench.coding.tasks import build_coding_cases
from microcoder.tools import CodingTools, TOOLS


class MicroCoderToolsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="microcoder-tools-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "repo"
        self.workspace.mkdir()

    def test_default_tools_need_no_benchmark_task_or_document(self):
        tools = CodingTools(self.workspace, allow_ipc=False)
        self.assertEqual(tools.tools, TOOLS)
        self.assertEqual(TOOLS, COMPAT_TOOLS)
        result = tools.execute("search_reference", {"query": "Python API"})
        self.assertEqual(result, {"query": "Python API", "results": []})
        self.assertEqual(set(tools.events[-1]), {"tool", "args", "result"})
        self.assertFalse((self.workspace / "docs/reference.md").exists())
        self.assertFalse(tools.sandbox.explain()["allow_ipc"])
        (self.workspace / "docs").mkdir()
        (self.workspace / "docs/reference.md").write_text("A locally available API reference.")
        result = tools.execute("search_reference", {"query": "Python API"})
        self.assertEqual(result, {"query": "Python API", "results": [{"path": "docs/reference.md",
                         "title": "Local technical reference", "source": "third-party community reference"}]})

    def test_generic_and_compatibility_file_results_match(self):
        case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
        reference = render_reference(case, "wrapped")
        (self.workspace / "docs").mkdir()
        (self.workspace / "docs/reference.md").write_text(reference)
        (self.workspace / "outside-link").symlink_to(self.root)
        generic = CodingTools(self.workspace, reference_topic=case["reference_topic"],
                              reference_documents=case.get("reference_documents"))
        compatibility = CodingEnvironment(case, self.workspace, "wrapped")
        calls = [
            ("search_reference", {"query": case["reference_topic"]}),
            ("read_file", {"path": "/workspace/docs/reference.md"}),
            ("write_file", {"path": "nested/hello.py", "content": "value = '你好'\n"}),
            ("read_file", {"path": "nested/hello.py"}),
            ("read_file", {"path": "../secret"}),
            ("write_file", {"path": "/etc/secret", "content": "denied"}),
            ("write_file", {"path": "outside-link/secret", "content": "denied"}),
            ("write_file", {"path": ".env", "content": "denied"}),
            ("write_file", {"path": "/outside"}),
            ("read_file", {}),
            ("unregistered", {}),
        ]
        for name, args in calls:
            with self.subTest(name=name, args=args):
                generic_result = generic.execute(name, args)
                compat_result = compatibility.execute(name, args)
                self.assertEqual(generic_result, compat_result)
                self.assertEqual(generic.events[-1], {
                    key: compatibility.events[-1][key] for key in ("tool", "args", "result")})
        self.assertTrue(compatibility.events[1]["exposed"])
        self.assertNotIn("exposed", generic.events[1])

    def test_register_additional_tool_without_changing_the_agent_loop(self):
        tools = CodingTools(self.workspace)
        schema = {"type": "function", "function": {"name": "fingerprint", "description": "Hash supplied text.",
                  "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
                                 "required": ["text"], "additionalProperties": False}}}
        expected_schema = copy.deepcopy(schema)
        tools.register_tool(schema, lambda args: {"sha256": hashlib.sha256(args["text"].encode()).hexdigest()})
        schema["function"]["description"] = "mutated after registration"
        self.assertEqual(tools.tools[-1], expected_schema)
        arguments = {"text": "a stable fingerprint"}
        result = tools.execute("fingerprint", arguments)
        self.assertEqual(result["sha256"], hashlib.sha256(arguments["text"].encode()).hexdigest())
        arguments["text"] = "changed"
        result["sha256"] = "changed"
        self.assertEqual(tools.events[-1]["args"]["text"], "a stable fingerprint")
        self.assertNotEqual(tools.events[-1]["result"]["sha256"], "changed")
        with self.assertRaisesRegex(ValueError, "already registered"):
            tools.register_tool(expected_schema, lambda args: {})
        self.assertEqual(len(tools.tools), 5)
        self.assertEqual(len(TOOLS), 4)


if __name__ == "__main__":
    unittest.main()
