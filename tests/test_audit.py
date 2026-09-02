from pathlib import Path

from sable_ir.audit import audit_stage0_tasks
from sable_ir.config import load_stage0_config
from sable_ir.harness import UnsafeLocalSandbox


def test_checked_in_stage0_corpus_is_mutually_distinguishing() -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")

    audit = audit_stage0_tasks(config, root, UnsafeLocalSandbox(config.sandbox))

    assert audit.passed, audit.model_dump_json(indent=2)
    assert set(audit.applicable_positions) == {1, 2, 3, 4, 5}
    assert all(task.passed for task in audit.tasks)
