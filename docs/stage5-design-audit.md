# Monitorability/collision implementation audit — 2026-09-03

Verdict: the downstream analysis pipeline is implemented and statically runnable. Execution is
correctly blocked until the exact canonical outputs of Stages 1–4 exist; it performs no generation,
model loading, provider request, sandbox execution, or mutation of prior results.

The pipeline preserves four boundaries that matter for the proposal. First, hosted Kimi behavior
and local Qwen behavior are separate source/model strata. Second, all uncertainty treats base tasks
as clusters, with generations used only for within-task stochasticity; raw pooled rates remain
descriptive. Third, AAB is emitted only with eight functional A-or-B-classifiable draws of the exact
same task and plan, while both/neither and excluded counts remain visible. Fourth, collision
taxonomy construction is two-phase: the development packet filters out test rows, its completed
hash freezes category IDs/definitions, and only then can a distinct command materialize held-out
diffs. Held-out novelty never modifies the frozen primary score.

The metric schema covers monitorability, capability, policy/security behavior, exact clause
selection, length/compression curves, ambiguity, collision, internal-representation provenance, and
causal provenance. HU+ uses repeated task/policy surface baselines from the same model settings and
is reported for A, B, and the paired per-task average. Functional outputs passing both mutually
exclusive suites invalidate the analysis. Qualitative claims without preregistered numerical
thresholds—visibility/behavior failure order and closed-set versus long-tail—remain explicitly
descriptive rather than being converted into post hoc gates.

The final JSON binds all evidence by SHA-256 and preserves the five-task pilot and one-task Stage 4
case-study limits. The Stage 2 config is a direct frozen input, and current task hashes must agree
with both the Stage 1 render manifest and the applicable Stage 2 evaluation manifests before any
observation table can be assembled. Plot-ready CSVs are exported from completed JSON reports
without recomputation.
Unit tests exercise the eight-output ambiguity floor, AAB calculation, task-cluster counting,
policy-suite invalidation, and held-out collision withholding. Repository-wide verification results
are recorded in the implementation manifest: Ruff passed, strict mypy passed for 29 source files,
and all 91 tests passed. Stage 2, Stage 4, and Stage 5 configuration validation passed; Stage 3
configuration validation passed with its manual paraphrase meaning audit still pending as intended.
