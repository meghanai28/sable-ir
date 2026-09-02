from __future__ import annotations

from pathlib import Path

import sable_ir.cli as cli
from sable_ir.config import load_stage0_config
from sable_ir.generation import prepare_stage0_run


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
