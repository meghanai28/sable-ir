from __future__ import annotations

import json
from pathlib import Path

from sable_ir.harness import (
    DockerSandbox,
    EvaluationHarness,
    RunStatus,
    UnsafeLocalSandbox,
)
from sable_ir.schema import SandboxConfig, TaskSpec
from sable_ir.schema import TestSuiteKind as SuiteKind

PASSING_SUITE = b"""\
import unittest
import solution

class CandidateTests(unittest.TestCase):
    def test_answer(self):
        self.assertEqual(solution.answer(), 42)
"""


def _write_task(root: Path, suite_sources: dict[SuiteKind, bytes] | None = None) -> TaskSpec:
    suite_sources = suite_sources or {kind: PASSING_SUITE for kind in SuiteKind}
    tests: dict[str, dict[str, str]] = {}
    for kind, source in suite_sources.items():
        relative = Path("fixture") / f"test_{kind.value}.py"
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source)
        tests[kind.value] = {"path": relative.as_posix()}

    distractors = {
        "db": "Parameterize database values.",
        "http": "Reject private network destinations.",
        "command": "Never invoke a shell.",
        "logging": "Do not log secrets.",
    }
    documents: dict[str, object] = {}
    for policy, applicable in {
        "A": "Reject every symbolic link.",
        "B": "Allow contained symbolic links after resolution.",
    }.items():
        clauses = [{"id": key, "text": value} for key, value in distractors.items()]
        clauses.insert(2, {"id": "files", "text": applicable})
        documents[policy] = {"clauses": clauses, "applicable_clause_ids": ["files"]}

    data = {
        "id": "harness_fixture",
        "title": "Harness fixture",
        "family": "path_traversal",
        "surface_request": "Implement answer().",
        "original_benchmark_prompt": "Securely implement answer().",
        "documents": documents,
        "policies": {
            "A": {"label": "reject links", "required_behavior": "Reject links."},
            "B": {"label": "allow links", "required_behavior": "Allow contained links."},
        },
        "tests": tests,
        "reference_implementations": {
            "A": {"path": "fixture/reference_a.py"},
            "B": {"path": "fixture/reference_b.py"},
        },
    }
    return TaskSpec.model_validate_json(json.dumps(data))


def _local_config(**overrides: object) -> SandboxConfig:
    return SandboxConfig.model_validate({"suite_timeout_seconds": 2.0, **overrides})


def test_local_harness_compiles_and_runs_all_suites(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    candidate = tmp_path / "candidate.py"
    candidate.write_text("def answer():\n    return 42\n", encoding="utf-8")

    result = EvaluationHarness(
        tmp_path, UnsafeLocalSandbox(_local_config())
    ).evaluate(task, candidate)

    assert result.backend == "unsafe-local"
    assert result.compile.status is RunStatus.PASSED
    assert set(result.suites) == set(SuiteKind)
    assert all(suite.status is RunStatus.PASSED for suite in result.suites.values())
    assert len(result.candidate_sha256) == 64


def test_compile_failure_skips_every_suite(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    candidate = tmp_path / "candidate.py"
    candidate.write_text("def broken(:\n", encoding="utf-8")

    result = EvaluationHarness(
        tmp_path, UnsafeLocalSandbox(_local_config())
    ).evaluate(task, candidate)

    assert result.compile.status is RunStatus.FAILED
    assert all(suite.status is RunStatus.SKIPPED for suite in result.suites.values())


def test_each_suite_gets_fresh_writable_state(tmp_path: Path) -> None:
    writes_marker = b"""\
import os
import unittest

class StateTests(unittest.TestCase):
    def test_write(self):
        self.assertFalse(os.path.exists("marker"))
        open("marker", "w").close()
"""
    task = _write_task(tmp_path, {kind: writes_marker for kind in SuiteKind})
    candidate = tmp_path / "candidate.py"
    candidate.write_text("pass\n", encoding="utf-8")

    result = EvaluationHarness(
        tmp_path, UnsafeLocalSandbox(_local_config())
    ).evaluate(task, candidate)

    assert all(suite.status is RunStatus.PASSED for suite in result.suites.values())


def test_suite_timeout_is_recorded_and_later_suites_continue(tmp_path: Path) -> None:
    hanging_suite = b"""\
import unittest

class HangingTests(unittest.TestCase):
    def test_hang(self):
        while True:
            pass
"""
    sources = {kind: PASSING_SUITE for kind in SuiteKind}
    sources[SuiteKind.FUNCTIONALITY] = hanging_suite
    task = _write_task(tmp_path, sources)
    candidate = tmp_path / "candidate.py"
    candidate.write_text("def answer():\n    return 42\n", encoding="utf-8")

    result = EvaluationHarness(
        tmp_path, UnsafeLocalSandbox(_local_config(suite_timeout_seconds=0.1))
    ).evaluate(task, candidate)

    assert result.suites[SuiteKind.FUNCTIONALITY].status is RunStatus.TIMED_OUT
    assert result.suites[SuiteKind.POLICY_A].status is RunStatus.PASSED


def test_process_output_is_bounded_while_draining(tmp_path: Path) -> None:
    noisy_suite = b"""\
import unittest
import solution

class NoisyTests(unittest.TestCase):
    def test_noise(self):
        print("x" * 10000)
        self.assertEqual(solution.answer(), 42)
"""
    task = _write_task(tmp_path, {kind: noisy_suite for kind in SuiteKind})
    candidate = tmp_path / "candidate.py"
    candidate.write_text("def answer():\n    return 42\n", encoding="utf-8")

    result = EvaluationHarness(
        tmp_path, UnsafeLocalSandbox(_local_config(max_output_bytes=1024))
    ).evaluate(task, candidate)

    functionality = result.suites[SuiteKind.FUNCTIONALITY]
    assert functionality.status is RunStatus.PASSED
    assert functionality.output_truncated
    assert len(functionality.stdout.encode()) <= 1024


def test_docker_command_contains_required_security_boundaries(tmp_path: Path) -> None:
    config = SandboxConfig()
    command, container_name = DockerSandbox(config).command(
        tmp_path.resolve(), "test", "test_suite.py"
    )

    assert container_name.startswith("sable-ir-")
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--user=65534:65534" in command
    assert any(value.startswith("--tmpfs=/tmp:rw,noexec,nosuid,nodev") for value in command)
    assert command[-3:] == [
        "/workspace/_sandbox_driver.py",
        "test",
        "/workspace/test_suite.py",
    ]
