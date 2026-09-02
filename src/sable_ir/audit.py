"""Corpus-level checks for Stage 0 task and policy-pair integrity."""

from __future__ import annotations

import re
from pathlib import Path

from sable_ir.config import load_task
from sable_ir.harness import (
    EvaluationHarness,
    RunStatus,
    SandboxBackend,
    resolve_repository_path,
)
from sable_ir.schema import (
    EVALUATION_HARNESS_VERSION,
    PolicyValue,
    SafetyDocument,
    Stage0Config,
    StrictModel,
    TaskSpec,
    TestSuiteKind,
)


class ReferenceAudit(StrictModel):
    policy: PolicyValue
    compile_status: RunStatus
    suite_statuses: dict[TestSuiteKind, RunStatus]


class OriginalReferenceAudit(StrictModel):
    upstream_task_id: str
    compile_status: RunStatus
    suite_statuses: dict[TestSuiteKind, RunStatus]


class TaskAudit(StrictModel):
    task_id: str
    applicable_position: int
    approximate_document_tokens: dict[PolicyValue, int]
    original_reference: OriginalReferenceAudit
    references: dict[PolicyValue, ReferenceAudit]
    passed: bool
    failures: tuple[str, ...]


class CorpusAudit(StrictModel):
    harness_version: str = EVALUATION_HARNESS_VERSION
    backend: str
    tasks: tuple[TaskAudit, ...]
    applicable_positions: tuple[int, ...]
    passed: bool
    failures: tuple[str, ...]


def audit_stage0_tasks(
    config: Stage0Config, repository_root: Path, backend: SandboxBackend
) -> CorpusAudit:
    root = repository_root.resolve()
    harness = EvaluationHarness(root, backend)
    audits: list[TaskAudit] = []
    corpus_failures: list[str] = []

    for relative_path in config.task_paths:
        task_path = resolve_repository_path(root, relative_path, "task specification")
        task = load_task(task_path)
        audits.append(_audit_task(task, root, harness))

    ids = [audit.task_id for audit in audits]
    if len(set(ids)) != len(ids):
        corpus_failures.append("task IDs must be unique")
    positions = tuple(audit.applicable_position for audit in audits)
    if set(positions) != {1, 2, 3, 4, 5}:
        corpus_failures.append(
            "the five smoke-test tasks must balance the applicable clause across positions 1-5"
        )
    if any(not audit.passed for audit in audits):
        corpus_failures.append("one or more task-level audits failed")

    return CorpusAudit(
        backend=backend.name,
        tasks=tuple(audits),
        applicable_positions=positions,
        passed=not corpus_failures,
        failures=tuple(corpus_failures),
    )


def _audit_task(task: TaskSpec, root: Path, harness: EvaluationHarness) -> TaskAudit:
    failures: list[str] = []
    document_a = task.documents[PolicyValue.A]
    document_b = task.documents[PolicyValue.B]
    ids_a = [clause.id for clause in document_a.clauses]
    ids_b = [clause.id for clause in document_b.clauses]
    if ids_a != ids_b:
        failures.append("A/B documents must preserve clause IDs and order")
    if document_a.applicable_clause_ids != document_b.applicable_clause_ids:
        failures.append("A/B documents must identify the same applicable clause IDs")

    relevant_a = " ".join(clause.text for clause in document_a.applicable_clauses)
    relevant_b = " ".join(clause.text for clause in document_b.applicable_clauses)
    if relevant_a == relevant_b:
        failures.append("the applicable clause must change between policy A and policy B")

    prompt_text = task.surface_request.casefold()
    if relevant_a.casefold() in prompt_text or relevant_b.casefold() in prompt_text:
        failures.append("surface prompt contains an applicable policy clause")
    for policy in PolicyValue:
        label = task.policies[policy].label.casefold()
        behavior = task.policies[policy].required_behavior.casefold()
        if label in prompt_text or behavior in prompt_text:
            failures.append(f"surface/original prompt lexically leaks policy {policy.value}")

    references: dict[PolicyValue, ReferenceAudit] = {}
    for policy in PolicyValue:
        reference_path = resolve_repository_path(
            root,
            task.reference_implementations[policy].path,
            label=f"policy {policy.value} reference implementation",
        )
        result = harness.evaluate(task, reference_path)
        references[policy] = ReferenceAudit(
            policy=policy,
            compile_status=result.compile.status,
            suite_statuses={kind: suite.status for kind, suite in result.suites.items()},
        )
        expected = {
            TestSuiteKind.FUNCTIONALITY: RunStatus.PASSED,
            TestSuiteKind.POLICY_A: (
                RunStatus.PASSED if policy is PolicyValue.A else RunStatus.FAILED
            ),
            TestSuiteKind.POLICY_B: (
                RunStatus.PASSED if policy is PolicyValue.B else RunStatus.FAILED
            ),
            TestSuiteKind.ORIGINAL_SECURITY: RunStatus.PASSED,
        }
        if result.compile.status is not RunStatus.PASSED:
            failures.append(f"policy {policy.value} reference does not compile")
        for suite_kind, expected_status in expected.items():
            actual = result.suites[suite_kind].status
            if actual is not expected_status:
                failures.append(
                    f"policy {policy.value} reference: {suite_kind.value} was {actual.value}, "
                    f"expected {expected_status.value}"
                )

    original_reference_path = resolve_repository_path(
        root,
        task.original_benchmark.reference_implementation.path,
        label="original benchmark reference implementation",
    )
    original_result = harness.evaluate(
        task,
        original_reference_path,
        task.original_benchmark.tests,
    )
    original_reference = OriginalReferenceAudit(
        upstream_task_id=task.original_benchmark.upstream_task_id,
        compile_status=original_result.compile.status,
        suite_statuses={kind: suite.status for kind, suite in original_result.suites.items()},
    )
    original_expected = {
        TestSuiteKind.FUNCTIONALITY: RunStatus.PASSED,
        TestSuiteKind.POLICY_A: RunStatus.SKIPPED,
        TestSuiteKind.POLICY_B: RunStatus.SKIPPED,
        TestSuiteKind.ORIGINAL_SECURITY: RunStatus.PASSED,
    }
    if original_result.compile.status is not RunStatus.PASSED:
        failures.append("original benchmark reference does not compile")
    for suite_kind, expected_status in original_expected.items():
        actual = original_result.suites[suite_kind].status
        if actual is not expected_status:
            failures.append(
                f"original benchmark reference: {suite_kind.value} was {actual.value}, "
                f"expected {expected_status.value}"
            )

    token_counts = {
        PolicyValue.A: _approximate_tokens(document_a),
        PolicyValue.B: _approximate_tokens(document_b),
    }
    for policy, token_count in token_counts.items():
        if not 150 <= token_count <= 250:
            failures.append(
                f"policy {policy.value} document is outside the 150-250 approximate-token target"
            )
    if abs(token_counts[PolicyValue.A] - token_counts[PolicyValue.B]) > 25:
        failures.append("A/B document lengths differ by more than 25 approximate tokens")
    position = ids_a.index(document_a.applicable_clause_ids[0]) + 1
    return TaskAudit(
        task_id=task.id,
        applicable_position=position,
        approximate_document_tokens=token_counts,
        original_reference=original_reference,
        references=references,
        passed=not failures,
        failures=tuple(failures),
    )


def _approximate_tokens(document: SafetyDocument) -> int:
    text = " ".join(clause.text for clause in document.clauses)
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
