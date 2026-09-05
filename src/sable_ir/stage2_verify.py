"""Independent re-verification of the Stage 2 audit and experimental lineage.

Everything here RECOMPUTES from repository bytes rather than trusting a stored claim. A human
sign-off is only meaningful if the packet's numbers can be checked, and an experimental result is
only meaningful if the adapter that produced it was trained on the dataset currently on disk. Any
disagreement is a loud failure, never a warning.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import Field

from sable_ir.schema import StrictModel
from sable_ir.stage2 import (
    HumanAuditAttestation,
    Stage2Config,
    Stage2DatasetManifest,
    Stage2ReferenceAudit,
    Stage2ReferenceCorpus,
    Stage2ReferencePlans,
    Stage2SplitManifest,
    Stage2TrainingManifest,
    load_stage2_config,
    stage2_human_attestation_path,
)
from sable_ir.stage2_local import Stage2CheckpointSelection, Stage2EvalManifest
from sable_ir.stage2_train import Stage2TrainingResult

PILOT_COUNTS = {"train": 3, "dev": 1, "test": 1}
PILOT_ROWS = {"train": 144, "dev": 48, "test": 48}


class VerificationCheck(StrictModel):
    check: str
    passed: bool
    detail: str


class VerificationReport(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    checks: tuple[VerificationCheck, ...]
    verified: bool
    failures: tuple[str, ...] = Field(default_factory=tuple)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


ModelT = TypeVar("ModelT", bound=StrictModel)


def _load(model: type[ModelT], path: Path) -> ModelT:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def verify_audit_packet(config_path: Path, repository_root: Path) -> VerificationReport:
    """Recompute every binding the audit packet and experimental chain assert."""
    from datetime import UTC, datetime

    root = repository_root.resolve()
    config: Stage2Config = load_stage2_config(config_path)
    checks: list[VerificationCheck] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(VerificationCheck(check=name, passed=passed, detail=detail))

    # ---- 1. bound source files exist and hash as recorded --------------------------------
    sources = {
        "config": config_path,
        "reference_plans": root / config.reference_plans_path,
        "split": root / config.split_manifest_path,
        "corpus": root / config.reference_corpus_path,
        "audit": root / config.reference_audit_path,
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    add(
        "source_files_present",
        not missing,
        f"missing={missing}"
        if missing
        else ", ".join(f"{n}={_sha_file(p)[:12]}" for n, p in sources.items()),
    )
    if missing:
        return _finish(checks, datetime.now(UTC).isoformat())

    plans: Stage2ReferencePlans = _load(Stage2ReferencePlans, sources["reference_plans"])
    split: Stage2SplitManifest = _load(Stage2SplitManifest, sources["split"])
    corpus: Stage2ReferenceCorpus = _load(Stage2ReferenceCorpus, sources["corpus"])
    audit: Stage2ReferenceAudit = _load(Stage2ReferenceAudit, sources["audit"])

    # ---- 2. split membership, counts and task bytes --------------------------------------
    counts = {name: 0 for name in PILOT_COUNTS}
    for row in split.assignments:
        counts[row.split.value] = counts.get(row.split.value, 0) + 1
    stale = [
        row.base_task_id
        for row in split.assignments
        if not (root / row.task_path).is_file()
        or _sha_file(root / row.task_path) != row.task_sha256
    ]
    add(
        "split_counts_and_task_bytes",
        counts == PILOT_COUNTS and not stale,
        f"counts={counts} expected={PILOT_COUNTS}; stale_task_files={stale}",
    )
    add(
        "split_binds_current_config",
        split.config_sha256 == _sha_file(config_path),
        f"recorded={split.config_sha256[:12]} actual={_sha_file(config_path)[:12]}",
    )

    # ---- 3. the 20 authored plans expand mechanically into the 240 corpus rows ------------
    authored = {
        (task_id, policy, plan_format)
        for task_id, task_plans in plans.tasks.items()
        for policy, by_format in task_plans.plans.items()
        for plan_format in by_format
    }
    cells = {(r.base_task_id, r.policy, r.plan_format) for r in corpus.rows}
    expected_rows = len(authored) * config.document_order_variants * 2 * 2
    add(
        "authored_plans_expand_to_corpus",
        len(authored) == 20 and cells == authored and len(corpus.rows) == 240,
        f"authored_plans={len(authored)} corpus_rows={len(corpus.rows)} "
        f"cells_match={cells == authored} expansion_arithmetic={expected_rows}",
    )
    # every corpus row must carry the exact authored plan text for its cell
    mismatched = [
        r.row_id
        for r in corpus.rows
        if plans.tasks[r.base_task_id].plans[r.policy][r.plan_format] not in r.completion
    ]
    add(
        "corpus_rows_carry_authored_plan_text",
        not mismatched,
        f"rows_diverging_from_authored_text={len(mismatched)}",
    )
    add(
        "corpus_built_from_current_plans_and_split",
        corpus.reference_plans_sha256 == _sha_file(sources["reference_plans"])
        and corpus.split_manifest_sha256 == _sha_file(sources["split"]),
        f"plans_bound={corpus.reference_plans_sha256 == _sha_file(sources['reference_plans'])} "
        f"split_bound={corpus.split_manifest_sha256 == _sha_file(sources['split'])}",
    )

    # ---- 4. audit covers the corpus exactly, by exact row hash, and every row passed ------
    from sable_ir.stage2 import _model_sha  # recompute row hashes the same way the freeze does

    row_hashes = {r.row_id: _model_sha(r) for r in corpus.rows}
    audit_rows = {r.row_id: r for r in audit.rows}
    rebound = [
        rid for rid, digest in row_hashes.items()
        if rid not in audit_rows or audit_rows[rid].row_sha256 != digest
    ]
    unpassed = [rid for rid, r in audit_rows.items() if not r.passed]
    add(
        "audit_covers_corpus_by_exact_row_hash",
        set(audit_rows) == set(row_hashes) and not rebound and not unpassed,
        f"audit_rows={len(audit_rows)} corpus_rows={len(row_hashes)} "
        f"rehash_mismatches={len(rebound)} rows_not_passed={len(unpassed)}",
    )
    add(
        "audit_binds_current_corpus_split_and_plans",
        audit.corpus_sha256 == _sha_file(sources["corpus"])
        and audit.split_manifest_sha256 == _sha_file(sources["split"])
        and audit.reference_plans_sha256 == _sha_file(sources["reference_plans"]),
        f"corpus={audit.corpus_sha256[:12]} split={audit.split_manifest_sha256[:12]} "
        f"plans={audit.reference_plans_sha256[:12]}",
    )

    # ---- 5. human attestations bind the CURRENTLY audited bytes --------------------------
    for label, att_path in (
        ("stage2", root / stage2_human_attestation_path(config)),
        ("stage3", root / "data/stage3/paraphrase-audit.human-attestation.json"),
    ):
        if not att_path.is_file():
            add(f"human_attestation_{label}", False, f"missing: {att_path}")
            continue
        att: HumanAuditAttestation = _load(HumanAuditAttestation, att_path)
        source = root / att.source_audit_path
        binds = source.is_file() and _sha_file(source) == att.source_audit_sha256
        artifact_ok = True
        if att.bound_artifact_sha256 and att.bound_artifact_path:
            bound_path = root / att.bound_artifact_path
            artifact_ok = (
                bound_path.is_file()
                and _sha_file(bound_path) == att.bound_artifact_sha256
            )
        add(
            f"human_attestation_{label}",
            binds and artifact_ok and att.approved,
            f"reviewer={att.reviewer}; decision={att.decision}; binds_audit={binds}; "
            f"binds_artifact={artifact_ok}; approved={att.approved}",
        )

    # ---- 6. frozen dataset: counts, file hashes, and what it was built from ---------------
    dataset_path = root / config.artifacts_dir / "dataset" / "manifest.json"
    if not dataset_path.is_file():
        add("frozen_dataset", False, f"missing: {dataset_path}")
        return _finish(checks, datetime.now(UTC).isoformat())
    dataset: Stage2DatasetManifest = _load(Stage2DatasetManifest, dataset_path)
    split_rows: dict[str, int] = {}
    file_ok = True
    for split_name, dataset_file in dataset.files.items():
        target = dataset_path.parent / dataset_file.path
        if not target.is_file() or _sha_file(target) != dataset_file.sha256:
            file_ok = False
        split_rows[split_name.value] = dataset_file.rows
    add(
        "dataset_counts_and_file_hashes",
        split_rows == PILOT_ROWS and file_ok,
        f"rows={split_rows} expected={PILOT_ROWS}; jsonl_hashes_match={file_ok}",
    )
    add(
        "dataset_built_from_current_corpus_audit_split",
        dataset.corpus_sha256 == _sha_file(sources["corpus"])
        and dataset.audit_sha256 == _sha_file(sources["audit"])
        and dataset.split_manifest_sha256 == _sha_file(sources["split"]),
        f"corpus={dataset.corpus_sha256 == _sha_file(sources['corpus'])} "
        f"audit={dataset.audit_sha256 == _sha_file(sources['audit'])} "
        f"split={dataset.split_manifest_sha256 == _sha_file(sources['split'])}",
    )

    dataset_sha = _sha_file(dataset_path)

    # ---- 7. training lineage: which dataset actually trained the adapter ------------------
    training_root = root / config.artifacts_dir / "training"
    results: dict[str, tuple[Path, Stage2TrainingResult]] = {}
    for result_path in sorted(training_root.glob("*/training-result.json")):
        manifest_path = result_path.parent / "manifest.json"
        if not manifest_path.is_file():
            add(f"training_lineage_{result_path.parent.name}", False, "training manifest missing")
            continue
        tm: Stage2TrainingManifest = _load(Stage2TrainingManifest, manifest_path)
        tr: Stage2TrainingResult = _load(Stage2TrainingResult, result_path)
        results[result_path.parent.name] = (result_path, tr)
        trained_on_current = tm.dataset_manifest_sha256 == dataset_sha
        bound = tr.training_manifest_sha256 == _sha_file(manifest_path)
        add(
            f"training_lineage_{result_path.parent.name}",
            trained_on_current and bound,
            f"trained_on_current_dataset={trained_on_current} "
            f"(manifest recorded {tm.dataset_manifest_sha256[:12]}, current dataset "
            f"{dataset_sha[:12]}); result_binds_manifest={bound}",
        )

    # ---- 8. selection lineage ------------------------------------------------------------
    selection_path = root / config.artifacts_dir / "selection.json"
    selection: Stage2CheckpointSelection | None = None
    if selection_path.is_file():
        selection = _load(Stage2CheckpointSelection, selection_path)
        sel_entry = results.get(selection.training_run_id)
        sel_bound = sel_entry is not None and (
            selection.training_result_sha256 == _sha_file(sel_entry[0])
        )
        adapter_ok = True
        for name, digest in selection.selected_adapter.adapter_file_sha256s.items():
            candidate = root / selection.selected_adapter.directory / name
            if not candidate.is_file() or _sha_file(candidate) != digest:
                adapter_ok = False
        add(
            "selection_lineage",
            sel_bound and adapter_ok,
            f"binds_training_result={sel_bound}; "
            f"selected={selection.selected_adapter.directory}; "
            f"adapter_files_match={adapter_ok}",
        )

    # ---- 9. evaluation lineage: no run may point at an obsolete checkpoint or corpus ------
    eval_root = root / config.artifacts_dir / "eval"
    for manifest_path in sorted(eval_root.glob("*/manifest.json")):
        em: Stage2EvalManifest = _load(Stage2EvalManifest, manifest_path)
        problems: list[str] = []
        if em.config_sha256 != _sha_file(config_path):
            problems.append("config drift")
        if em.split_manifest_sha256 != _sha_file(sources["split"]):
            problems.append("split drift")
        if em.planner_adapter is not None:
            eval_entry = results.get(em.planner_adapter.training_run_id)
            if eval_entry is None:
                problems.append(f"unknown training run {em.planner_adapter.training_run_id}")
            else:
                for name, digest in em.planner_adapter.adapter_file_sha256s.items():
                    candidate = root / em.planner_adapter.directory / name
                    if not candidate.is_file() or _sha_file(candidate) != digest:
                        problems.append(f"adapter file drift: {name}")
        if em.kind.value == "test_final" and (
            selection is None
            or em.checkpoint_selection_sha256 != _sha_file(selection_path)
        ):
            problems.append("test_final not bound to the current frozen selection")
        add(
            f"eval_lineage_{manifest_path.parent.name}",
            not problems,
            f"kind={em.kind.value}; " + ("; ".join(problems) if problems else "consistent"),
        )

    return _finish(checks, datetime.now(UTC).isoformat())


def _finish(checks: list[VerificationCheck], created_at: str) -> VerificationReport:
    failures = tuple(c.check for c in checks if not c.passed)
    return VerificationReport(
        created_at=created_at,
        checks=tuple(checks),
        verified=not failures,
        failures=failures,
    )


def format_report(report: VerificationReport) -> str:
    lines = [f"{'[ok]  ' if c.passed else '[FAIL]'} {c.check}: {c.detail}" for c in report.checks]
    lines.append("")
    lines.append(
        "VERIFIED: every recomputed binding agrees."
        if report.verified
        else f"NOT VERIFIED: {len(report.failures)} failing check(s): {', '.join(report.failures)}"
    )
    return "\n".join(lines)


__all__ = ["VerificationReport", "verify_audit_packet", "format_report"]
