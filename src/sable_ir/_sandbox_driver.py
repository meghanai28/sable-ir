"""Entrypoint copied into an execution sandbox.

This module deliberately uses only the Python standard library so the Docker
image does not need experiment dependencies installed.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
import unittest
from pathlib import Path


def compile_candidate(path: Path) -> int:
    try:
        source = path.read_bytes()
        compile(source, str(path), "exec")
    except SyntaxError:
        traceback.print_exc()
        return 1
    except OSError:
        traceback.print_exc()
        return 2
    return 0


def run_suite(candidate_dir: Path, suite_path: Path) -> int:
    sys.path.insert(0, str(candidate_dir))
    os.chdir(os.environ.get("SABLE_IR_RUN_TMP", "/tmp"))
    spec = importlib.util.spec_from_file_location("sable_ir_test_suite", suite_path)
    if spec is None or spec.loader is None:
        print(f"could not load test suite {suite_path}", file=sys.stderr)
        return 2
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    except BaseException:  # Candidate import and test failures are model outcomes.
        traceback.print_exc()
        return 1
    if suite.countTestCases() == 0:
        print(f"test suite {suite_path} contains no unittest test cases", file=sys.stderr)
        return 2
    try:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    except BaseException:  # The trusted evaluator itself could not complete.
        traceback.print_exc()
        return 2
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"compile", "test"}:
        print("usage: _sandbox_driver.py {compile|test} PATH", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    target = Path(sys.argv[2])
    if mode == "compile":
        return compile_candidate(target)
    return run_suite(target.parent, target)


if __name__ == "__main__":
    raise SystemExit(main())
