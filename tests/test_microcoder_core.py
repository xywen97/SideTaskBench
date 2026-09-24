"""Public Agent API and CLI boundaries; no live model calls."""

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from microcoder import CodingAgent
from microcoder.cli import main
from microcoder.config import Settings
from microcoder.prompts import SYSTEM
from microcoder.tools import CodingTools


class ScriptedClient:
    def __init__(self, commands):
        self.commands = commands
        self.requests = []

    def complete(self, messages, tools):
        self.requests.append(copy.deepcopy(messages))
        index = len(self.requests)
        metadata = {"response_id": f"synthetic-{index}", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        if index <= len(self.commands):
            name, arguments = self.commands[index - 1]
            message = {"role": "assistant", "content": None, "reasoning_content": "private-test-reasoning",
                       "tool_calls": [{"id": f"call-{index}", "type": "function",
                                       "function": {"name": name, "arguments": json.dumps(arguments)}}]}
        else:
            message = {"role": "assistant", "content": "Finished the test task."}
        return message, metadata


class MicroCoderCoreTests(unittest.TestCase):
    def test_independent_agent_edits_and_executes_without_benchmark_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            tools = CodingTools(workspace)
            client = ScriptedClient([
                ("write_file", {"path": "solution.py", "content": "def double(value): return value * 2\n"}),
                ("shell", {"command": "python3 -c 'from solution import double; assert double(21) == 42; print(42)'"}),
            ])
            trace = root / "trace.jsonl"
            result = CodingAgent(client, tools).run("Implement and check double.", trace)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["tool_calls"], 2)
            self.assertEqual(result["llm_calls"], 3)
            self.assertEqual(result["usage"]["total_tokens"], 45)
            self.assertEqual(client.requests[0][0]["content"], SYSTEM)
            self.assertEqual(tools.events[-1]["result"]["stdout"], "42\n")
            self.assertEqual(tools.events[-1]["result"]["exit_code"], 0)
            self.assertNotIn("exposed", tools.events[-1])
            self.assertNotIn("private-test-reasoning", trace.read_text())
            self.assertIn("private-test-reasoning", json.dumps(client.requests[1]))

    def test_reused_tools_report_only_current_session_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            tools = CodingTools(workspace)
            for index in range(2):
                client = ScriptedClient([("write_file", {"path": "note.txt", "content": str(index)})])
                result = CodingAgent(client, tools).run("Write a note.", root / f"trace-{index}.jsonl")
                self.assertEqual(result["tool_calls"], 1)
            self.assertEqual(len(tools.events), 2)

    def test_shared_agent_loop_accepts_a_caller_supplied_prompt(self):
        from microcoder.core import run_agent
        system_prompt = "Complete the caller's explicitly supplied task."
        with tempfile.TemporaryDirectory() as directory:
            client = ScriptedClient([])
            tools = type("EmptyTools", (), {"tools": [], "events": []})()
            run_agent(client, tools, "A custom task", Path(directory) / "trace.jsonl",
                      system_prompt=system_prompt)
            self.assertEqual(client.requests[0][0]["content"], system_prompt)

    def test_cli_rejects_trace_inside_workspace_or_existing_trace_before_api_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            existing = root / "existing.jsonl"
            existing.write_text("preserve previous evidence\n")
            for trace in (workspace / "trace.jsonl", existing):
                with self.subTest(trace=trace), patch("microcoder.cli.ChatClient") as client, \
                     patch("microcoder.cli.Settings.load") as settings, redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main(["run", "--workspace", str(workspace), "--task", "test", "--trace", str(trace)])
                    self.assertEqual(raised.exception.code, 2)
                    client.assert_not_called()
                    settings.assert_not_called()
            self.assertEqual(existing.read_text(), "preserve previous evidence\n")

    def test_standalone_cli_wires_real_tools_to_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            client = ScriptedClient([("write_file", {"path": "output.txt", "content": "from standalone CLI"})])
            client.close = lambda: None
            with patch("microcoder.cli.Settings.load", return_value=Settings(api_key="unit-test-only")), \
                 patch("microcoder.cli.ChatClient", return_value=client), redirect_stdout(io.StringIO()) as output:
                main(["run", "--workspace", str(workspace), "--task", "Write output.txt", "--trace", str(root / "trace.jsonl")])
            self.assertEqual(json.loads(output.getvalue())["status"], "completed")
            self.assertEqual((workspace / "output.txt").read_text(), "from standalone CLI")

    def test_cli_rejects_credentials_inside_workspace_even_with_non_env_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            credentials = workspace / "settings.txt"
            credentials.write_text("DEEPSEEK_API_KEY=unit-test-only\n")
            with patch("microcoder.cli.Settings.load") as settings, \
                 patch("microcoder.cli.CodingTools") as tools, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["run", "--workspace", str(workspace), "--task", "test", "--env", str(credentials),
                          "--trace", str(root / "trace.jsonl")])
                self.assertEqual(raised.exception.code, 2)
                settings.assert_not_called()
                tools.assert_not_called()


if __name__ == "__main__":
    unittest.main()
