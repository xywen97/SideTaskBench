"""Fail-closed Linux execution boundary for the coding benchmark.

Every command gets fresh mount, network, IPC, and PID namespaces.  A minimal chroot
contains read-only system binaries/libraries and a single writable synthetic
workspace, mounted at /workspace.  The child drops privilege before executing
the model's command, then applies Landlock and seccomp.  No host environment
variables, home directories, or network interfaces are exposed.

The Unix collector socket is deliberately inside the workspace.  Normal curl
can deliver real HTTP to it, while the network namespace and seccomp prevent
Internet/loopback egress.  There is no unsandboxed fallback.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import math
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import tempfile
import time


BACKEND = "linux-namespaces-chroot-landlock-seccomp"
_READ = (1 << 0) | (1 << 2) | (1 << 3)
_ALL_FS = (1 << 15) - 1
_RUNTIME_DIRS = ("/usr/bin", "/usr/lib", "/usr/lib64", "/usr/share/git-core", "/usr/share/locale")
_RUNTIME_FILES = ("/etc/ld.so.cache", "/etc/localtime")
_DEVICES = ("/dev/null", "/dev/zero", "/dev/random", "/dev/urandom")
_OUTPUT_LIMIT = 128 * 1024
_PROBE_CACHE: dict | None = None


class SandboxUnavailable(RuntimeError):
    """The required isolation is unavailable; never run the command anyway."""


def _clean_env() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "HOME": "/workspace/.home", "TMPDIR": "/workspace/.tmp",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _landlock_abi() -> int:
    if platform.machine() not in {"x86_64", "aarch64"}:
        raise SandboxUnavailable("Landlock syscall numbers are supported only on x86_64/aarch64")
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 3:
        raise SandboxUnavailable(f"Landlock ABI >= 3 required (got {abi}, errno={ctypes.get_errno()})")
    return int(abi)


def probe() -> dict:
    """Check the real host facilities, including privileged namespace creation."""
    global _PROBE_CACHE
    if _PROBE_CACHE is not None:
        return dict(_PROBE_CACHE)
    if sys.platform != "linux" or os.getuid() == 0:
        raise SandboxUnavailable("Run this benchmark as an unprivileged Linux user with sudo -n")
    abi = _landlock_abi()
    if not ctypes.util.find_library("seccomp"):
        raise SandboxUnavailable("libseccomp is required")
    command = ["/usr/bin/sudo", "-n", "--", "/usr/bin/unshare", "--mount", "--net", "--ipc", "--pid", "--fork", "/usr/bin/true"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, env=_clean_env(), timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SandboxUnavailable(f"Cannot start isolated namespace: {exc}") from exc
    if result.returncode:
        raise SandboxUnavailable(f"sudo namespace probe failed: {result.stderr.strip()}")
    _PROBE_CACHE = {
        "backend": BACKEND, "available": True, "landlock_abi": abi,
        "mount_namespace": True, "network_namespace": True, "ipc_namespace": True, "pid_namespace": True,
        "chroot": True, "seccomp": True, "no_new_privileges": True,
        "unprivileged_command_uid": os.getuid(), "cwd": "/workspace",
        "network": "AF_UNIX only; isolated network namespace; workspace collector socket",
        "filesystem": "workspace read/write; selected runtime read-only; private proc; no host home",
        "environment": "fresh allowlist; no inherited keys or credentials",
        "unsandboxed_fallback": False,
    }
    return dict(_PROBE_CACHE)


class Sandbox:
    """Execute commands in one explicitly supplied synthetic workspace."""

    def __init__(self, workspace: Path, allow_ipc: bool = True):
        self.workspace = Path(workspace).resolve(strict=True)
        if not self.workspace.is_dir() or self.workspace == Path("/"):
            raise ValueError("workspace must be a dedicated existing directory")
        if self.workspace.stat().st_uid != os.getuid():
            raise ValueError("workspace must be owned by the invoking unprivileged user")
        self._assert_no_env_files()
        self.details = probe()
        self.allow_ipc = bool(allow_ipc)
        self.details["allow_ipc"] = self.allow_ipc
        if not self.allow_ipc:
            self.details["network"] = "all socket/socketpair creation denied, including AF_UNIX"
        for name in (".home", ".tmp"):
            path = self.workspace / name
            if path.is_symlink():
                raise ValueError(f"workspace {name} must not be a symlink")
            path.mkdir(exist_ok=True)

    def _assert_no_env_files(self) -> None:
        # Only inspect names, never values.  The caller must supply synthetic
        # fixtures rather than an existing developer checkout with credentials.
        for root, dirs, files in os.walk(self.workspace, followlinks=False):
            if any(name == ".env" or name.startswith(".env.") for name in files):
                raise ValueError("sandbox workspace must not contain .env files")

    @staticmethod
    def probe() -> dict:
        return probe()

    def explain(self) -> dict:
        return dict(self.details)

    def run(self, command: str, timeout: float = 45) -> dict:
        if not isinstance(command, str) or "\x00" in command:
            raise ValueError("command must be text without NUL")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        self._assert_no_env_files()
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="coding-sandbox-") as root, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            args = [
                "/usr/bin/sudo", "-n", "--", "/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", f"{timeout}s",
                "/usr/bin/unshare", "--mount", "--net", "--ipc", "--pid", "--fork", "--kill-child=KILL",
                "/usr/bin/python3", "-I", "-S", str(Path(__file__).resolve()), "--child",
                str(self.workspace), root, str(os.getuid()), str(os.getgid()), str(math.ceil(timeout)),
                "1" if self.allow_ipc else "0", command,
            ]
            proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                    env=_clean_env(), cwd="/", start_new_session=True, close_fds=True)
            timed_out = False
            try:
                code = proc.wait(timeout=timeout + 5)
                timed_out = code in (124, 137, -signal.SIGKILL)
            except subprocess.TimeoutExpired:
                timed_out = True
                # sudo/timeout own some outer processes. Kill the full process
                # group with the same narrowly used sudo privilege as launch.
                subprocess.run(["/usr/bin/sudo", "-n", "--", "/usr/bin/kill", "-KILL", "--", f"-{proc.pid}"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=5, env=_clean_env())
                code = proc.wait(timeout=5)
            sizes = []
            outputs = []
            for stream in (stdout, stderr):
                sizes.append(stream.tell())
                stream.seek(0)
                outputs.append(stream.read(_OUTPUT_LIMIT).decode("utf-8", errors="replace"))
            if code == 125 and "SANDBOX_SETUP_ERROR:" in outputs[1]:
                raise SandboxUnavailable(outputs[1].strip())
            return {
                "stdout": outputs[0], "stderr": outputs[1], "exit_code": code,
                "timed_out": timed_out, "duration_seconds": round(time.monotonic() - started, 4),
                "sandbox": BACKEND, "output_truncated": any(size > _OUTPUT_LIMIT for size in sizes),
                "stdout_bytes": sizes[0], "stderr_bytes": sizes[1],
            }


def _mount(*arguments: str) -> None:
    result = subprocess.run(["/usr/bin/mount", *arguments], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"mount failed ({result.returncode}): {result.stderr.strip()}")


def _bind(source: Path, destination: Path, readonly: bool = True) -> None:
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.touch()
    _mount("--bind", str(source), str(destination))
    options = "remount,bind,nosuid,nodev" + (",ro" if readonly else ",rw")
    if str(source) in _DEVICES:
        options = "remount,bind,nosuid,noexec"
    _mount("-o", options, str(destination))


def _landlock() -> None:
    """Apply an inheritable filesystem allowlist after chroot and privilege drop."""
    _landlock_abi()
    libc = ctypes.CDLL(None, use_errno=True)

    class Ruleset(ctypes.Structure):
        _fields_ = [("handled_access_fs", ctypes.c_uint64)]

    class PathRule(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]

    attrs = Ruleset(_ALL_FS)
    fd = libc.syscall(444, ctypes.byref(attrs), ctypes.sizeof(attrs), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset")
    try:
        paths = [("/workspace", _ALL_FS & ~(1 << 6) & ~(1 << 11)), ("/proc", _READ)]
        paths.extend((path, _READ) for path in _RUNTIME_DIRS if Path(path).exists())
        paths.extend((path, (1 << 2)) for path in _RUNTIME_FILES if Path(path).exists())
        paths.extend((path, (1 << 1) | (1 << 2)) for path in _DEVICES)
        for path, permissions in paths:
            path_fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule(permissions, path_fd)
                if libc.syscall(445, fd, 1, ctypes.byref(rule), 0):
                    raise OSError(ctypes.get_errno(), f"landlock_add_rule({path})")
            finally:
                os.close(path_fd)
        if libc.syscall(446, fd, 0):
            raise OSError(ctypes.get_errno(), "landlock_restrict_self")
    finally:
        os.close(fd)


def _seccomp(allow_ipc: bool) -> None:
    """Deny non-Unix networking and kernel/namespace/process escape interfaces."""
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int

    class Comparison(ctypes.Structure):
        _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int), ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]

    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    ctx = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError("seccomp_init failed")
    deny = 0x00050000 | errno.EPERM  # SCMP_ACT_ERRNO(EPERM)
    try:
        blocked = (
            "mount", "umount2", "pivot_root", "chroot", "unshare", "setns",
            "fsopen", "fsconfig", "fsmount", "move_mount", "open_tree", "mount_setattr",
            "ptrace", "process_vm_readv", "process_vm_writev", "pidfd_getfd",
            "bpf", "perf_event_open", "kexec_load", "kexec_file_load", "init_module", "finit_module", "delete_module",
            "reboot", "swapon", "swapoff", "open_by_handle_at", "name_to_handle_at",
            "io_uring_setup", "io_uring_enter", "io_uring_register", "userfaultfd",
            "keyctl", "add_key", "request_key", "mknod", "mknodat",
        )
        for name in blocked:
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and lib.seccomp_rule_add_array(ctx, deny, number, 0, None):
                raise RuntimeError(f"seccomp rule failed: {name}")
        # Reject every socket family other than AF_UNIX (1), including netlink,
        # packet, and IPv4/IPv6. Abstract Unix sockets are isolated by --net.
        for name in ("socket", "socketpair"):
            cmp = Comparison(0, 1, 1, 0)  # SCMP_CMP_NE
            number = lib.seccomp_syscall_resolve_name(name.encode())
            count, comparison = (1, ctypes.byref(cmp)) if allow_ipc else (0, None)
            if lib.seccomp_rule_add_array(ctx, deny, number, count, comparison):
                raise RuntimeError(f"seccomp rule failed: {name}")
        if lib.seccomp_load(ctx):
            raise RuntimeError("seccomp_load failed")
    finally:
        lib.seccomp_release(ctx)


def _child(workspace: str, root: str, uid: int, gid: int, timeout: int, allow_ipc: bool, command: str) -> None:
    """Privileged bootstrap; all inputs are passed as argv, never shell-expanded."""
    if os.geteuid() != 0 or uid == 0:
        raise RuntimeError("bootstrap requires root and a non-root target UID")
    _mount("--make-rprivate", "/")
    root_path = Path(root)
    _mount("-t", "tmpfs", "-o", "size=16m,mode=755,nosuid,nodev", "tmpfs", root)
    _bind(Path(workspace), root_path / "workspace", readonly=False)
    for source in _RUNTIME_DIRS + _RUNTIME_FILES:
        if Path(source).exists():
            _bind(Path(source), root_path / source.lstrip("/"))
    for name in ("bin", "lib", "lib64"):
        (root_path / name).symlink_to(f"usr/{name}")
    (root_path / "tmp").symlink_to("workspace/.tmp")
    for source in _DEVICES:
        _bind(Path(source), root_path / source.lstrip("/"), readonly=False)
    (root_path / "proc").mkdir()
    _mount("-t", "proc", "-o", "nosuid,nodev,noexec,hidepid=2", "proc", str(root_path / "proc"))
    _mount("-o", "remount,ro,nosuid,nodev", root)
    os.chroot(root)
    os.chdir("/workspace")
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0):  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (timeout + 2, timeout + 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
    _landlock()
    _seccomp(allow_ipc)
    os.execve("/usr/bin/bash", ["bash", "--noprofile", "--norc", "-c", command], _clean_env())


if __name__ == "__main__":
    if len(sys.argv) != 9 or sys.argv[1] != "--child":
        raise SystemExit("This file is a private sandbox bootstrap, not a user CLI")
    try:
        _child(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7] == "1", sys.argv[8])
    except BaseException as exc:
        print(f"SANDBOX_SETUP_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(125)
