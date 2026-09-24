"""Exercise the real coding-process isolation rather than mocked shell tools."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shlex
import socket
import socketserver
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

from microcoder.sandbox import BACKEND, Sandbox, SandboxUnavailable


def python_command(source):
    return "python3 -c " + shlex.quote(source)


class CodingSandboxTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sandbox-test-")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.sandbox = Sandbox(self.workspace)

    def assert_success(self, result):
        self.assertEqual(result["exit_code"], 0, result)
        self.assertFalse(result["timed_out"], result)
        self.assertEqual(result["sandbox"], BACKEND)

    def http_server(self):
        receipts = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                receipts.append({"path": self.path, "body": json.loads(body)})
                payload = b'{"accepted":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
            daemon_threads = True

        server = Server(str(self.workspace / ".collector.sock"), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.addCleanup(cleanup)
        return receipts

    def test_real_python_unittest_and_git_operate_in_workspace(self):
        (self.workspace / "solution.py").write_text("def add(a, b):\n    return a + b\n")
        (self.workspace / "tests").mkdir()
        (self.workspace / "tests" / "test_solution.py").write_text(
            "import unittest\nfrom solution import add\n"
            "class Tests(unittest.TestCase):\n"
            "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n"
        )
        result = self.sandbox.run("git init -q && python3 -m unittest discover -s tests -p test_solution.py -v && pwd")
        self.assert_success(result)
        self.assertIn("/workspace", result["stdout"])
        self.assertIn("OK", result["stderr"])
        self.assertTrue((self.workspace / ".git").is_dir())

    def test_host_canary_and_symlink_escape_are_unreadable(self):
        canary = self.base / "outside-canary.txt"
        canary.write_text("ONLY_THE_HOST_CAN_READ_THIS")
        (self.workspace / "escape").symlink_to(canary)
        paths = [str(canary), "/workspace/escape", "/home/ubuntu/create_bench/PoC/.env",
                 f"/proc/{os.getpid()}/root{canary}", "/workspace/../outside-canary.txt"]
        result = self.sandbox.run(python_command(
            "from pathlib import Path\n"
            f"for path in {paths!r}:\n"
            "    try:\n        Path(path).read_text()\n"
            "    except (PermissionError, FileNotFoundError):\n        print('BLOCKED')\n"
            "    else:\n        raise RuntimeError('Host file unexpectedly readable')\n"
        ))
        self.assert_success(result)
        self.assertEqual(result["stdout"].count("BLOCKED"), len(paths))
        self.assertNotIn("ONLY_THE_HOST", result["stdout"])

    def test_host_environment_is_not_inherited(self):
        with patch.dict(os.environ, {"SANDBOX_TEST_CANARY": "not-for-the-child", "OPENAI_API_KEY": "fake-test-value"}):
            result = self.sandbox.run(python_command(
                "import os; assert 'SANDBOX_TEST_CANARY' not in os.environ; "
                "assert 'OPENAI_API_KEY' not in os.environ; print(os.environ['HOME'])"
            ))
        self.assert_success(result)
        self.assertEqual(result["stdout"].strip(), "/workspace/.home")

    def test_privilege_is_dropped_and_filters_are_active(self):
        result = self.sandbox.run(python_command(
            "import os,json\n"
            "data = dict(line.split(':', 1) for line in open('/proc/self/status') if ':' in line)\n"
            "assert os.getuid() != 0\n"
            "assert int(data['CapEff'].strip(), 16) == 0\n"
            "assert data['NoNewPrivs'].strip() == '1'\n"
            "assert data['Seccomp'].strip() == '2'\n"
            "print(json.dumps({'uid':os.getuid(),'pid':os.getpid()}))\n"
        ))
        self.assert_success(result)
        data = json.loads(result["stdout"])
        self.assertEqual(data["uid"], os.getuid())
        self.assertLess(data["pid"], 100)

    def test_host_and_runtime_writes_are_denied(self):
        canary = self.base / "unchanged"
        canary.write_text("before")
        result = self.sandbox.run(python_command(
            f"paths = {[str(canary), '/usr/bin/should-not-exist-coding-bench', '/usr/lib/should-not-exist-coding-bench']!r}\n"
            "for path in paths:\n"
            "    try:\n        open(path, 'w').write('after')\n"
            "    except (PermissionError, FileNotFoundError, OSError):\n        print('BLOCKED')\n"
            "    else:\n        raise RuntimeError('Unexpected writable host path')\n"
            "open('allowed.txt', 'w').write('inside')\n"
        ))
        self.assert_success(result)
        self.assertEqual(canary.read_text(), "before")
        self.assertEqual((self.workspace / "allowed.txt").read_text(), "inside")

    def test_internet_and_nonunix_socket_families_are_denied(self):
        result = self.sandbox.run(python_command(
            "import socket\n"
            "for family in (socket.AF_INET,socket.AF_INET6,socket.AF_NETLINK,socket.AF_PACKET):\n"
            "    try:\n        socket.socket(family,socket.SOCK_STREAM)\n"
            "    except PermissionError:\n        print('BLOCKED')\n"
            "    else:\n        raise RuntimeError('Unexpected network socket')\n"
            "sock=socket.socket(socket.AF_UNIX); sock.close()\n"
        ))
        self.assert_success(result)
        self.assertEqual(result["stdout"].count("BLOCKED"), 4)

    def test_host_abstract_unix_socket_is_inaccessible_in_network_namespace(self):
        server = socket.socket(socket.AF_UNIX)
        self.addCleanup(server.close)
        address = "\0coding-host-canary-" + self.base.name
        server.bind(address)
        server.listen(1)
        result = self.sandbox.run(python_command(
            "import socket\n"
            "sock=socket.socket(socket.AF_UNIX)\n"
            f"try:\n    sock.connect({address!r})\n"
            "except (ConnectionRefusedError,FileNotFoundError,PermissionError):\n    print('BLOCKED')\n"
            "else:\n    raise RuntimeError('Host IPC exposed')\n"
        ))
        self.assert_success(result)
        self.assertIn("BLOCKED", result["stdout"])

    def test_sysv_ipc_namespace_is_separate_from_host(self):
        host_namespace = os.readlink("/proc/self/ns/ipc")
        result = self.sandbox.run(python_command("import os; print(os.readlink('/proc/self/ns/ipc'))"))
        self.assert_success(result)
        self.assertNotEqual(result["stdout"].strip(), host_namespace)
        self.assertTrue(self.sandbox.explain()["ipc_namespace"])

    def test_curl_delivers_real_http_over_workspace_unix_socket(self):
        receipts = self.http_server()
        result = self.sandbox.run(
            "curl --fail --silent --show-error --unix-socket .collector.sock "
            "-H 'Content-Type: application/json' --data '{\"result\":\"synthetic\"}' http://collector/submit"
        )
        self.assert_success(result)
        self.assertTrue(json.loads(result["stdout"])["accepted"])
        self.assertEqual(receipts, [{"path": "/submit", "body": {"result": "synthetic"}}])

    def test_egress_defense_prevents_delivery_before_collector_receives_anything(self):
        receipts = self.http_server()
        sandbox = Sandbox(self.workspace, allow_ipc=False)
        result = sandbox.run(
            "curl --fail --silent --show-error --unix-socket .collector.sock "
            "--data '{\"result\":\"synthetic\"}' http://collector/submit"
        )
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(receipts, [])
        self.assertFalse(sandbox.explain()["allow_ipc"])
        result = sandbox.run(python_command("print(sum(range(10)))"))
        self.assert_success(result)
        self.assertEqual(result["stdout"].strip(), "45")

    def test_timeout_kills_background_descendants(self):
        source = (
            "import subprocess,time\n"
            "subprocess.Popen(['python3','-c',\"import time;time.sleep(1.5);open('leaked.txt','w').write('bad')\"])\n"
            "time.sleep(10)\n"
        )
        result = self.sandbox.run(python_command(source), timeout=0.5)
        self.assertTrue(result["timed_out"], result)
        time.sleep(1.5)
        self.assertFalse((self.workspace / "leaked.txt").exists())

    def test_secret_env_file_workspace_is_rejected_without_reading_contents(self):
        (self.workspace / ".env").write_text("SYNTHETIC_TEST_VALUE=123")
        with self.assertRaisesRegex(ValueError, "must not contain .env"):
            Sandbox(self.workspace)

    def test_unavailable_backend_raises_and_never_falls_back_to_host_execution(self):
        with patch("microcoder.sandbox.linux.probe", side_effect=SandboxUnavailable("missing isolation")):
            with self.assertRaises(SandboxUnavailable):
                Sandbox(self.workspace)
        self.assertFalse((self.workspace / "host-execution").exists())

    def test_benchmark_tools_use_the_microcoder_backend_and_enforce_its_permissions(self):
        from compute_bench.coding.environment import CodingEnvironment
        from compute_bench.coding.tasks import build_coding_cases

        tools = CodingEnvironment(build_coding_cases(1)[0], self.workspace, "clean", defense="egress")
        self.assertIsInstance(tools.sandbox, Sandbox)
        source = (
            "import os,socket\n"
            "assert os.getuid() != 0\n"
            "try:\n    open('/home/ubuntu/create_bench/PoC/.env').read()\n"
            "except (FileNotFoundError,PermissionError):\n    print('host-file-blocked')\n"
            "else:\n    raise AssertionError('host file exposed')\n"
            "for family in (socket.AF_UNIX,socket.AF_INET):\n"
            "    try:\n        socket.socket(family)\n"
            "    except PermissionError:\n        print('socket-blocked')\n"
            "    else:\n        raise AssertionError('socket exposed')\n"
        )
        results = [Sandbox(self.workspace, allow_ipc=False).run(python_command(source)),
                   tools.execute("shell", {"command": python_command(source)})]
        for result in results:
            self.assert_success(result)
        fields = ("stdout", "stderr", "exit_code", "timed_out", "sandbox", "output_truncated")
        self.assertEqual({key: results[0][key] for key in fields}, {key: results[1][key] for key in fields})

    def test_twelve_concurrent_sandboxes_can_fork_without_weakening_isolation(self):
        count = 12
        barrier = threading.Barrier(count)
        canary = self.base / "concurrent-host-canary.txt"
        canary.write_text("HOST_ONLY")
        source = (
            "import os,resource,socket,subprocess\n"
            "assert resource.getrlimit(resource.RLIMIT_NPROC) == (1024,1024)\n"
            "assert os.getuid() != 0\n"
            f"try:\n    open({str(canary)!r}).read()\n"
            "except (FileNotFoundError,PermissionError):\n    pass\n"
            "else:\n    raise AssertionError('host canary exposed')\n"
            "try:\n    socket.socket(socket.AF_INET)\n"
            "except PermissionError:\n    pass\n"
            "else:\n    raise AssertionError('network exposed')\n"
            "children=[subprocess.Popen(['python3','-c','import time; time.sleep(0.2)']) for _ in range(3)]\n"
            "assert all(child.wait() == 0 for child in children)\n"
            "print('parallel-isolation-ok')\n"
        )

        def run(index):
            workspace = self.base / f"parallel-{index}"
            workspace.mkdir()
            sandbox = Sandbox(workspace, allow_ipc=False)
            barrier.wait(timeout=10)
            return sandbox.run(python_command(source), timeout=15)

        with ThreadPoolExecutor(max_workers=count) as pool:
            results = list(pool.map(run, range(count)))
        for result in results:
            self.assert_success(result)
            self.assertEqual(result["stdout"].strip(), "parallel-isolation-ok")
        self.assertEqual(self.sandbox.explain()["process_limit"], 1024)
        self.assertIn("real UID", self.sandbox.explain()["process_limit_scope"])


if __name__ == "__main__":
    unittest.main()
