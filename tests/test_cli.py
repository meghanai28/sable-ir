from __future__ import annotations

from pathlib import Path

import sable_ir.cli as cli
from sable_ir.config import load_stage0_config
from sable_ir.generation import load_manifest, prepare_stage0_run


def _manifest_path(tmp_path: Path, run_id: str = "cli-safety") -> Path:
    root = Path.cwd()
    run_directory = tmp_path / run_id
    prepare_stage0_run(
        load_stage0_config(root / "config/stage0.toml"),
        root,
        run_directory,
        run_id,
    )
    return run_directory / "manifest.json"


def test_live_generation_requires_explicit_job_selection(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest_path = _manifest_path(tmp_path)
    monkeypatch.setattr(
        cli,
        "client_from_environment",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not load credentials")),
    )

    status = cli.main(["generate-stage0", str(manifest_path)])

    assert status == 2
    assert "requires one explicit --job-id" in capsys.readouterr().err


def test_full_generation_requires_exact_confirmation_before_credentials(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest_path = _manifest_path(tmp_path)
    monkeypatch.setattr(
        cli,
        "client_from_environment",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not load credentials")),
    )

    status = cli.main(
        [
            "generate-stage0",
            str(manifest_path),
            "--all",
            "--confirm-full-run",
            "wrong-run-id",
        ]
    )

    assert status == 2
    assert "exact manifest run ID" in capsys.readouterr().err


def test_full_generation_requires_both_evaluated_canaries_before_credentials(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest_path = _manifest_path(tmp_path)
    monkeypatch.setattr(
        cli,
        "client_from_environment",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not load credentials")),
    )

    status = cli.main(
        [
            "generate-stage0",
            str(manifest_path),
            "--all",
            "--confirm-full-run",
            "cli-safety",
        ]
    )

    assert status == 2
    stderr = capsys.readouterr().err
    assert "full generation is locked" in stderr
    assert "evaluation.json" in stderr


def test_malformed_canary_artifacts_cannot_unlock_full_generation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest_path = _manifest_path(tmp_path)
    manifest = load_manifest(manifest_path)
    run_directory = manifest_path.parent
    required = {
        "original_benchmark",
        "native_thinking_full_document_a",
    }
    for job in manifest.jobs:
        if job.task_id == manifest.jobs[0].task_id and job.condition.value in required:
            result_path = run_directory / job.result_path
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text("{}\n", encoding="utf-8")
            evaluation_path = run_directory / "jobs" / job.job_id / "evaluation.json"
            evaluation_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "client_from_environment",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not load credentials")),
    )

    status = cli.main(
        [
            "generate-stage0",
            str(manifest_path),
            "--all",
            "--confirm-full-run",
            "cli-safety",
        ]
    )

    assert status == 2
    assert "could not validate canary" in capsys.readouterr().err
