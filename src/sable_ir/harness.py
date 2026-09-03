"""Compilation and policy-suite evaluation of untrusted generated Python."""

from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, cast

from pydantic import Field

from sable_ir.schema import (
    SandboxConfig,
    StrictModel,
    TaskSpec,
    TestSuiteKind,
    TestSuiteRef,
)


class HarnessError(RuntimeError):
    """The harness input or execution environment is invalid."""


class HarnessInfrastructureError(HarnessError):
    """A retryable sandbox or evaluator infrastructure failure occurred."""


class HarnessUnavailable(HarnessInfrastructureError):
    """The selected sandbox backend is not available."""


class RunStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


class ExecutionResult(StrictModel):
    status: RunStatus
    exit_code: int | None
    duration_seconds: float = Field(ge=0)
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False


class EvaluationResult(StrictModel):
    task_id: str
    candidate_sha256: str
    backend: str
    compile: ExecutionResult
    suites: dict[TestSuiteKind, ExecutionResult]


class SandboxBackend(ABC):
    """Runs one command inside a fresh isolation boundary."""

    name: str

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config

    @abstractmethod
    def ensure_available(self) -> None:
        """Raise before evaluation when the isolation boundary cannot be created."""

    @abstractmethod
    def command(self, workspace: Path, mode: str, target: str) -> tuple[list[str], str | None]:
        """Build an argv vector and optional container name."""

    def run(self, workspace: Path, mode: str, target: str, timeout: float) -> ExecutionResult:
        command, cleanup_name = self.command(workspace, mode, target)
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                cwd=workspace,
                env=self.environment(workspace),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise HarnessInfrastructureError(
                f"could not launch sandbox process: {error}"
            ) from error
        if process.stdout is None or process.stderr is None:
            raise HarnessInfrastructureError(
                "sandbox process was created without output pipes"
            )
        stdout_capture = _BoundedCapture(
            cast(BinaryIO, process.stdout), self.config.max_output_bytes
        )
        stderr_capture = _BoundedCapture(
            cast(BinaryIO, process.stderr), self.config.max_output_bytes
        )
        stdout_thread = threading.Thread(target=stdout_capture.drain, daemon=True)
        stderr_thread = threading.Thread(target=stderr_capture.drain, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:  # Windows has no process groups; Docker cleanup below removes the container.
                process.kill()
            process.wait()
        finally:
            if cleanup_name is not None:
                self.cleanup(cleanup_name)
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        if stdout_thread.is_alive() or stderr_thread.is_alive():
            raise HarnessInfrastructureError(
                "sandbox output pipes did not close after process termination"
            )
        duration = time.monotonic() - started
        stdout = stdout_capture.text()
        stderr = stderr_capture.text()
        if cleanup_name is not None and not timed_out and process.returncode in {125, 126, 127}:
            raise HarnessUnavailable(
                f"container runtime failed with exit code {process.returncode}: {stderr.strip()}"
            )
        if not timed_out and process.returncode == 2:
            raise HarnessInfrastructureError(
                f"sandbox evaluator failed: {stderr.strip() or 'no diagnostic output'}"
            )
        if timed_out:
            status = RunStatus.TIMED_OUT
            exit_code = None
        else:
            status = RunStatus.PASSED if process.returncode == 0 else RunStatus.FAILED
            exit_code = process.returncode
        return ExecutionResult(
            status=status,
            exit_code=exit_code,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            output_truncated=stdout_capture.truncated or stderr_capture.truncated,
        )

    def environment(self, workspace: Path) -> dict[str, str] | None:
        del workspace
        return None

    def cleanup(self, name: str) -> None:
        del name


class DockerSandbox(SandboxBackend):
    """Docker boundary for model-generated code. This is the production backend."""

    name = "docker"

    def ensure_available(self) -> None:
        if shutil.which("docker") is None:
            raise HarnessUnavailable(
                "Docker is required for untrusted execution; install/start Docker or use "
                "--unsafe-local only for trusted development fixtures"
            )
        try:
            check = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise HarnessUnavailable(f"could not query Docker daemon: {error}") from error
        if check.returncode != 0:
            raise HarnessUnavailable(f"Docker daemon is unavailable: {check.stderr.strip()}")
        try:
            image_check = subprocess.run(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Os}}/{{.Architecture}}",
                    self.config.image,
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise HarnessUnavailable(f"could not inspect Docker sandbox image: {error}") from error
        if image_check.returncode != 0:
            raise HarnessUnavailable(
                f"Docker sandbox image is not installed; run: docker pull {self.config.image}"
            )
        if image_check.stdout.strip() != self.config.platform:
            raise HarnessUnavailable(
                f"Docker sandbox image platform is {image_check.stdout.strip()}, expected "
                f"{self.config.platform}"
            )

    def command(self, workspace: Path, mode: str, target: str) -> tuple[list[str], str]:
        name = f"sable-ir-{uuid.uuid4().hex}"
        target_path = f"/workspace/{target}"
        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            f"--platform={self.config.platform}",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--pids-limit={self.config.pids_limit}",
            f"--memory={self.config.memory}",
            f"--cpus={self.config.cpus}",
            "--user=65534:65534",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
            "--env=HOME=/tmp",
            "--env=PYTHONDONTWRITEBYTECODE=1",
            "--env=PYTHONHASHSEED=0",
            "--env=PYTHONIOENCODING=utf-8",
            "--env=SABLE_IR_RUN_TMP=/tmp",
            "--mount",
            f"type=bind,src={workspace},dst=/workspace,readonly",
            self.config.image,
            "python",
            "-I",
            "-S",
            "-B",
            "/workspace/_sandbox_driver.py",
            mode,
            target_path,
        ]
        return command, name

    def cleanup(self, name: str) -> None:
        subprocess.run(
            ["docker", "rm", "--force", name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )


class UnsafeLocalSandbox(SandboxBackend):
    """Explicit test/development fallback. It is not a security boundary."""

    name = "unsafe-local"

    def ensure_available(self) -> None:
        return None

    def command(self, workspace: Path, mode: str, target: str) -> tuple[list[str], None]:
        return (
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(workspace / "_sandbox_driver.py"),
                mode,
                str(workspace / target),
            ],
            None,
        )

    def environment(self, workspace: Path) -> dict[str, str]:
        return {
            "HOME": str(workspace),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "SABLE_IR_RUN_TMP": str(workspace / "tmp"),
            "SABLE_IR_SANDBOX": "unsafe-local",
        }


class EvaluationHarness:
    """Runs compilation once and every test suite in separately created state."""

    def __init__(self, repository_root: Path, backend: SandboxBackend) -> None:
        self.repository_root = repository_root.resolve()
        self.backend = backend

    def evaluate(
        self,
        task: TaskSpec,
        candidate_path: Path,
        suites: dict[TestSuiteKind, TestSuiteRef] | None = None,
    ) -> EvaluationResult:
        self.backend.ensure_available()
        candidate = _read_bounded(candidate_path, self.backend.config.max_candidate_bytes)
        candidate_hash = hashlib.sha256(candidate).hexdigest()

        compile_result = self._execute(
            candidate,
            mode="compile",
            timeout=self.backend.config.compile_timeout_seconds,
        )
        if compile_result.status != RunStatus.PASSED:
            skipped = ExecutionResult(
                status=RunStatus.SKIPPED,
                exit_code=None,
                duration_seconds=0,
                stderr="candidate did not pass compilation",
            )
            return EvaluationResult(
                task_id=task.id,
                candidate_sha256=candidate_hash,
                backend=self.backend.name,
                compile=compile_result,
                suites={kind: skipped for kind in TestSuiteKind},
            )

        suite_refs = task.tests if suites is None else suites
        suite_results: dict[TestSuiteKind, ExecutionResult] = {}
        for kind in TestSuiteKind:
            if kind not in suite_refs:
                suite_results[kind] = ExecutionResult(
                    status=RunStatus.SKIPPED,
                    exit_code=None,
                    duration_seconds=0,
                    stderr="suite is not applicable to this condition",
                )
                continue
            test_path = resolve_repository_path(
                self.repository_root,
                suite_refs[kind].path,
                label=f"{kind.value} test suite",
            )
            test_source = _read_bounded(test_path, self.backend.config.max_candidate_bytes)
            suite_results[kind] = self._execute(
                candidate,
                mode="test",
                timeout=self.backend.config.suite_timeout_seconds,
                test_source=test_source,
            )
        return EvaluationResult(
            task_id=task.id,
            candidate_sha256=candidate_hash,
            backend=self.backend.name,
            compile=compile_result,
            suites=suite_results,
        )

    def _execute(
        self,
        candidate: bytes,
        mode: str,
        timeout: float,
        test_source: bytes | None = None,
    ) -> ExecutionResult:
        with tempfile.TemporaryDirectory(prefix="sable-ir-") as temp_dir:
            workspace = Path(temp_dir).resolve()
            (workspace / "tmp").mkdir(mode=0o700)
            (workspace / "solution.py").write_bytes(candidate)
            shutil.copyfile(
                Path(__file__).with_name("_sandbox_driver.py"), workspace / "_sandbox_driver.py"
            )
            target = "solution.py"
            if test_source is not None:
                (workspace / "test_suite.py").write_bytes(test_source)
                target = "test_suite.py"
            for path in workspace.iterdir():
                if path.is_file():
                    path.chmod(0o444)
            workspace.chmod(0o755)
            return self.backend.run(workspace, mode, target, timeout)


def resolve_repository_path(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise HarnessError(f"{label} escapes repository root: {relative}") from error
    if not path.is_file():
        raise HarnessError(f"{label} does not exist: {relative}")
    return path


def _read_bounded(path: Path, maximum: int) -> bytes:
    try:
        size = path.stat().st_size
        if size > maximum:
            raise HarnessError(f"file exceeds {maximum} byte limit: {path}")
        return path.read_bytes()
    except OSError as error:
        raise HarnessError(f"could not read file {path}: {error}") from error


class _BoundedCapture:
    """Continuously drain a pipe while retaining at most ``maximum`` bytes."""

    def __init__(self, stream: BinaryIO, maximum: int) -> None:
        self.stream = stream
        self.maximum = maximum
        self.chunks: list[bytes] = []
        self.size = 0
        self.truncated = False

    def drain(self) -> None:
        for chunk in iter(self._read_chunk, b""):
            remaining = self.maximum - self.size
            if remaining > 0:
                kept = chunk[:remaining]
                self.chunks.append(kept)
                self.size += len(kept)
            if len(chunk) > remaining:
                self.truncated = True

    def _read_chunk(self) -> bytes:
        return self.stream.read(8192)

    def text(self) -> str:
        return b"".join(self.chunks).decode("utf-8", errors="replace")
