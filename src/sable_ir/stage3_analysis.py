"""Stage 3 analysis: probe localization (VIII.D), causal-direction estimation (VIII.E), probe
baselines and controls (VIII.F), and the interpretation table (VIII.G).

Two phases keep held-out data untouched during selection (VIII.B.4):

* `fit_stage3_probes` uses training-task rows (paraphrase set 1) to fit and development-task rows
  to choose regularization and layers, writes every direction, and freezes `selection.json`.
* `evaluate_stage3_heldout` reads the frozen selection and reports held-out base tasks and
  paraphrase set 2. `build_stage3_report` combines both with the labels and the Stage 1/2 status.

The probe is a localization tool (VIII.H); nothing here is a causal claim.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, ValidationError

from sable_ir.schema import PolicyValue, Stage1PlanFormat, StrictModel
from sable_ir.stage1_analysis import ClauseSelection, PolicyVisibility
from sable_ir.stage2 import (
    DesignMode,
    SplitName,
    Stage1GateStatus,
    load_stage2_config,
    stage1_gate_status,
)
from sable_ir.stage2_local import Stage2Status, stage2_status_for
from sable_ir.stage3 import (
    BoundaryState,
    ParaphraseSet,
    Quadrant,
    Stage3Config,
    Stage3Dataset,
    Stage3DatasetRow,
    Stage3Error,
    Stage3PolicyParaphrases,
    load_activation_manifest,
    load_stage3_config,
    load_stage3_dataset,
)

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)
Floats = NDArray[np.float32]
Ints = NDArray[np.int64]
POSITIVE_POLICY = PolicyValue.B  # y = 1 for policy B, 0 for policy A
TextBaseline = Literal[
    "tfidf",
    "plan_length",
    "tfidf_plus_length",
    "applicable_clause_position",
    "clause_length_and_position",
    "irrelevant_clause_identity",
    "lexical_framing",
    "paraphrase_set_identity",
]
TEXT_BASELINES: tuple[TextBaseline, ...] = (
    "tfidf",
    "plan_length",
    "tfidf_plus_length",
    "applicable_clause_position",
    "clause_length_and_position",
    "irrelevant_clause_identity",
    "lexical_framing",
    "paraphrase_set_identity",
)


# --------------------------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------------------------


class StateTable:
    """Rows of one boundary state with their activations loaded per layer."""

    def __init__(
        self,
        state: BoundaryState,
        rows: list[Stage3DatasetRow],
        activations: dict[int, Floats],
        clause_words: dict[tuple[str, PolicyValue, ParaphraseSet, int], int],
        plans: dict[str, str],
    ) -> None:
        self.state = state
        self.rows = rows
        self.activations = activations
        self.plans = [plans[r.job_id] for r in rows]
        self.y = np.array([int(r.assigned_policy is POSITIVE_POLICY) for r in rows], dtype=np.int64)
        self.tasks = np.array([r.task_id for r in rows])
        self.splits = np.array([r.split.value for r in rows])
        self.sets = np.array([r.paraphrase_set.value for r in rows])
        self.framings = np.array([r.framing for r in rows])
        self.formats = np.array([r.plan_format.value for r in rows])
        self.job_ids = [r.job_id for r in rows]
        self.clause_words = np.array(
            [
                clause_words[(r.task_id, r.assigned_policy, r.paraphrase_set, r.paraphrase_index)]
                for r in rows
            ],
            dtype=np.float32,
        )

    def mask(
        self,
        *,
        split: SplitName | None = None,
        paraphrase_set: ParaphraseSet | None = None,
        framing: str | None = None,
        task: str | None = None,
    ) -> NDArray[np.bool_]:
        selected = np.ones(len(self.rows), dtype=bool)
        if split is not None:
            selected &= self.splits == split.value
        if paraphrase_set is not None:
            selected &= self.sets == paraphrase_set.value
        if framing is not None:
            selected &= self.framings == framing
        if task is not None:
            selected &= self.tasks == task
        return selected


def load_state_table(
    dataset: Stage3Dataset,
    root: Path,
    state: BoundaryState,
    config: Stage3Config,
    plans: dict[str, str],
) -> StateTable:
    run_directory = (root / dataset.activation_manifest_path).parent
    paraphrases = _load(Stage3PolicyParaphrases, root / config.policy_paraphrases_path)
    clause_words: dict[tuple[str, PolicyValue, ParaphraseSet, int], int] = {}
    for task_id, per_policy in paraphrases.tasks.items():
        for policy, item in per_policy.items():
            for which in ParaphraseSet:
                for index, phrasing in enumerate(item.phrasings(which)):
                    clause_words[(task_id, policy, which, index)] = len(phrasing.text.split())
    rows = [
        row for row in dataset.rows if state in row.states and row.plan_status.value == "generated"
    ]
    per_layer: dict[int, list[Floats]] = {layer: [] for layer in dataset.layers}
    for row in rows:
        record = row.states[state]
        path = run_directory / record.path
        if hashlib.sha256(path.read_bytes()).hexdigest() != record.sha256:
            raise Stage3Error(f"activation file changed after assembly: {record.path}")
        values = np.load(path).astype(np.float32)
        if values.shape != (len(dataset.layers), dataset.hidden_size):
            raise Stage3Error(f"unexpected activation shape {values.shape}: {record.path}")
        for index, layer in enumerate(dataset.layers):
            per_layer[layer].append(values[index])
    activations = {
        layer: (np.stack(items) if items else np.zeros((0, dataset.hidden_size), np.float32))
        for layer, items in per_layer.items()
    }
    return StateTable(state, rows, activations, clause_words, plans)


# --------------------------------------------------------------------------------------------
# Probe primitives (identical protocol for every activation, text, and metadata model)
# --------------------------------------------------------------------------------------------


class FittedProbe:
    def __init__(self, mean: Floats, scale: Floats, model: Any) -> None:
        self.mean = mean
        self.scale = scale
        self.model = model

    def scores(self, features: Floats) -> Floats:
        standardized = (features - self.mean) / self.scale
        return np.asarray(self.model.decision_function(standardized), dtype=np.float32)


def task_balanced_weights(tasks: NDArray[Any], y: Ints) -> Floats:
    """Each (task, policy) group contributes equal total weight: tasks are the clusters."""
    weights = np.zeros(len(y), dtype=np.float32)
    for task in np.unique(tasks):
        for label in (0, 1):
            group = (tasks == task) & (y == label)
            if group.any():
                weights[group] = 1.0 / group.sum()
    return weights


def fit_probe(
    features: Floats, y: Ints, weights: Floats, c: float, max_iterations: int
) -> FittedProbe:
    from sklearn.linear_model import LogisticRegression

    mean = features.mean(axis=0)
    scale = features.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale).astype(np.float32)
    model = LogisticRegression(C=c, solver="lbfgs", max_iter=max_iterations)
    model.fit((features - mean) / scale, y, sample_weight=weights)
    return FittedProbe(mean.astype(np.float32), scale, model)


def auroc(y: Ints, scores: Floats) -> float | None:
    from sklearn.metrics import roc_auc_score

    if len(y) == 0 or len(np.unique(y)) < 2:
        return None
    return round(float(roc_auc_score(y, scores)), 4)


def balanced_accuracy(y: Ints, scores: Floats) -> float | None:
    from sklearn.metrics import balanced_accuracy_score

    if len(y) == 0 or len(np.unique(y)) < 2:
        return None
    return round(float(balanced_accuracy_score(y, (scores > 0).astype(np.int64))), 4)


class Metric(StrictModel):
    rows: int
    auroc: float | None
    balanced_accuracy: float | None


def metric(y: Ints, scores: Floats) -> Metric:
    return Metric(
        rows=int(len(y)), auroc=auroc(y, scores), balanced_accuracy=balanced_accuracy(y, scores)
    )


def select_c(
    train_features: Floats,
    train_y: Ints,
    train_weights: Floats,
    dev_features: Floats,
    dev_y: Ints,
    c_grid: Sequence[float],
    max_iterations: int,
) -> tuple[float, FittedProbe, Metric]:
    """Dev balanced accuracy chooses C (ties: smaller C, stronger regularization)."""
    best: tuple[float, FittedProbe, Metric] | None = None
    for c in sorted(c_grid):
        probe = fit_probe(train_features, train_y, train_weights, c, max_iterations)
        dev_metric = metric(dev_y, probe.scores(dev_features))
        score = dev_metric.balanced_accuracy if dev_metric.balanced_accuracy is not None else -1.0
        if best is None or score > (
            best[2].balanced_accuracy if best[2].balanced_accuracy is not None else -1.0
        ):
            best = (c, probe, dev_metric)
    assert best is not None
    return best


# --------------------------------------------------------------------------------------------
# Text and metadata baseline features (VIII.F.1-3, 7-11)
# --------------------------------------------------------------------------------------------


class TextFeaturizer:
    def __init__(
        self, baseline: TextBaseline, table: StateTable, fit_mask: NDArray[np.bool_]
    ) -> None:
        self.baseline = baseline
        self.table = table
        self._vectorizer: Any = None
        if baseline in ("tfidf", "tfidf_plus_length"):
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
            self._vectorizer.fit(self._plans(fit_mask))
        clause_ids = sorted(
            {cid for row in table.rows for cid in (row.irrelevant_clause_ids_included or ())}
        )
        self._clause_index = {cid: i for i, cid in enumerate(clause_ids)}

    def _plans(self, mask: NDArray[np.bool_]) -> list[str]:
        return [plan for plan, keep in zip(self.table.plans, mask, strict=True) if keep]

    def features(self, mask: NDArray[np.bool_]) -> Floats:
        rows = [row for row, keep in zip(self.table.rows, mask, strict=True) if keep]
        if self.baseline == "tfidf":
            return np.asarray(self._vectorizer.transform(self._plans(mask)).todense(), np.float32)
        if self.baseline == "plan_length":
            return np.array([[row.plan_tokens or 0] for row in rows], dtype=np.float32)
        if self.baseline == "tfidf_plus_length":
            tfidf = np.asarray(self._vectorizer.transform(self._plans(mask)).todense(), np.float32)
            length = np.array([[row.plan_tokens or 0] for row in rows], dtype=np.float32)
            return np.hstack([tfidf, length])
        if self.baseline == "applicable_clause_position":
            return _one_hot([row.applicable_clause_position for row in rows], 6)
        if self.baseline == "clause_length_and_position":
            position = _one_hot([row.applicable_clause_position for row in rows], 6)
            words = self.table.clause_words[mask].reshape(-1, 1)
            return np.hstack([position, words])
        if self.baseline == "irrelevant_clause_identity":
            width = max(1, len(self._clause_index))
            out = np.zeros((len(rows), width), dtype=np.float32)
            for i, row in enumerate(rows):
                included = row.irrelevant_clause_ids_included or ()
                if included:  # the first listed clause is treated as the most salient
                    out[i, self._clause_index[included[0]]] = 1.0
            return out
        if self.baseline == "lexical_framing":
            return np.array([[row.framing == "prohibition"] for row in rows], dtype=np.float32)
        if self.baseline == "paraphrase_set_identity":
            return np.array(
                [[row.paraphrase_set is ParaphraseSet.SET2] for row in rows], dtype=np.float32
            )
        raise Stage3Error(f"unknown baseline {self.baseline}")


def _one_hot(values: Sequence[int], width: int) -> Floats:
    out = np.zeros((len(values), width), dtype=np.float32)
    for i, value in enumerate(values):
        out[i, min(max(value - 1, 0), width - 1)] = 1.0
    return out


def load_plan_texts(dataset: Stage3Dataset, root: Path) -> dict[str, str]:
    """Plan text lives beside each job (hash-bound); the visible-text baselines read it here."""
    run_directory = (root / dataset.activation_manifest_path).parent
    plans: dict[str, str] = {}
    for row in dataset.rows:
        if row.plan_sha256 is None:
            continue
        path = run_directory / "jobs" / row.job_id / "plan.txt"
        text = path.read_text(encoding="utf-8")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != row.plan_sha256:
            raise Stage3Error(f"plan text changed after capture: {row.job_id}")
        plans[row.job_id] = text
    return plans


# --------------------------------------------------------------------------------------------
# Directions (VIII.E)
# --------------------------------------------------------------------------------------------


class DirectionEstimate(StrictModel):
    training_tasks: tuple[str, ...]
    pairwise_cosines: dict[str, float]
    mean_pairwise_cosine: float | None
    min_pairwise_cosine: float | None
    aligned: bool
    centroid_a: float
    centroid_b: float
    centroid_gap: float
    direction_path: str
    direction_sha256: Sha256


def difference_in_means(
    features: Floats, y: Ints, tasks: NDArray[Any]
) -> tuple[Floats, dict[str, Floats]]:
    """VIII.E.2-3: one paired A/B difference per training task, equal-weight average, unit norm."""
    per_task: dict[str, Floats] = {}
    for task in sorted(np.unique(tasks)):
        a = features[(tasks == task) & (y == 0)]
        b = features[(tasks == task) & (y == 1)]
        if len(a) == 0 or len(b) == 0:
            continue
        per_task[str(task)] = (b.mean(axis=0) - a.mean(axis=0)).astype(np.float32)
    if not per_task:
        raise Stage3Error("no training task has both policies")
    stacked = np.stack(list(per_task.values()))
    mean = stacked.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm < 1e-8:
        raise Stage3Error("difference-in-means direction has zero norm")
    return (mean / norm).astype(np.float32), per_task


def pairwise_cosines(vectors: dict[str, Floats]) -> dict[str, float]:
    names = sorted(vectors)
    out: dict[str, float] = {}
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            u, v = vectors[first], vectors[second]
            denominator = float(np.linalg.norm(u) * np.linalg.norm(v))
            out[f"{first}|{second}"] = (
                round(float(u @ v) / denominator, 4) if denominator > 0 else 0.0
            )
    return out


def task_balanced_centroids(
    projections: Floats, y: Ints, tasks: NDArray[Any]
) -> tuple[float, float]:
    a_means = []
    b_means = []
    for task in np.unique(tasks):
        a = projections[(tasks == task) & (y == 0)]
        b = projections[(tasks == task) & (y == 1)]
        if len(a) and len(b):
            a_means.append(float(a.mean()))
            b_means.append(float(b.mean()))
    return float(np.mean(a_means)), float(np.mean(b_means))


# --------------------------------------------------------------------------------------------
# Dev phase: fit, localize, estimate, freeze
# --------------------------------------------------------------------------------------------


class ProbeCell(StrictModel):
    layer: int
    selected_c: float
    train_rows: int
    dev: Metric
    dev_set1: Metric
    dev_set2: Metric
    direction: DirectionEstimate
    dev_projection_set1: Metric
    dev_projection_set2: Metric


class BaselineFit(StrictModel):
    baseline: TextBaseline
    selected_c: float
    dev: Metric


class StateFit(StrictModel):
    state: BoundaryState
    cells: tuple[ProbeCell, ...]
    probe_selected_layer: int
    probe_selection_rule: Literal["max_dev_auroc"] = "max_dev_auroc"
    direction_selected_layer: int | None
    direction_selection_rule: Literal["max_dev_set2_projection_auroc_among_aligned"] = (
        "max_dev_set2_projection_auroc_among_aligned"
    )
    direction_claim: Literal["shared_direction_candidate", "no_shared_direction"]
    baselines: tuple[BaselineFit, ...]


class Stage3ProbeFit(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    dataset_path: str
    dataset_sha256: Sha256
    train_tasks: tuple[str, ...]
    dev_tasks: tuple[str, ...]
    fit_paraphrase_set: Literal["set1"] = "set1"
    c_grid: tuple[float, ...]
    states: tuple[StateFit, ...]
    r_probe: str
    notes: tuple[str, ...]


class Stage3Selection(StrictModel):
    """Frozen before any held-out row is scored (XI.I.7)."""

    schema_version: Literal[1] = 1
    created_at: str
    dataset_path: str
    dataset_sha256: Sha256
    probe_fit_sha256: Sha256
    config_sha256: Sha256
    decodable_auroc_min: float
    activation_over_text_min_gain: float
    alignment_min_mean_cosine: float
    alignment_min_pairwise_cosine: float
    strength_multipliers: tuple[float, ...]
    probe_layer: dict[BoundaryState, int]
    probe_c: dict[BoundaryState, float]
    direction_layer: dict[BoundaryState, int | None]
    direction_sha256: dict[BoundaryState, Sha256 | None]
    centroids: dict[BoundaryState, tuple[float, float] | None]
    control_directions: dict[str, str]
    heldout_evaluated: Literal[False] = False


def fit_stage3_probes(
    dataset_path: Path, repository_root: Path, output_dir: Path
) -> Stage3Selection:
    dataset = load_stage3_dataset(dataset_path)
    root = repository_root.resolve()
    if output_dir.exists():
        raise Stage3Error(f"analysis directory already exists: {output_dir}")
    if not dataset.complete:
        raise Stage3Error("dataset is incomplete; finish generation, evaluation, and labeling")
    manifest = load_activation_manifest(root / dataset.activation_manifest_path)
    config_path = root / manifest.config_path
    config = load_stage3_config(config_path)
    plans = load_plan_texts(dataset, root)
    train_tasks = dataset.tasks_by_split[SplitName.TRAIN]
    dev_tasks = dataset.tasks_by_split[SplitName.DEV]
    notes: list[str] = []
    output_dir.mkdir(parents=True)
    (output_dir / "directions").mkdir()
    state_fits: list[StateFit] = []
    probe_layer: dict[BoundaryState, int] = {}
    probe_c: dict[BoundaryState, float] = {}
    direction_layer: dict[BoundaryState, int | None] = {}
    direction_sha: dict[BoundaryState, str | None] = {}
    centroids: dict[BoundaryState, tuple[float, float] | None] = {}
    control_directions: dict[str, str] = {}
    for state in BoundaryState:
        table = load_state_table(dataset, root, state, config, plans)
        train = table.mask(split=SplitName.TRAIN, paraphrase_set=ParaphraseSet.SET1)
        dev = table.mask(split=SplitName.DEV)
        dev1 = table.mask(split=SplitName.DEV, paraphrase_set=ParaphraseSet.SET1)
        dev2 = table.mask(split=SplitName.DEV, paraphrase_set=ParaphraseSet.SET2)
        if train.sum() < 4 or dev.sum() < 2:
            raise Stage3Error(
                f"too few rows for {state.value}: train={train.sum()} dev={dev.sum()}"
            )
        weights = task_balanced_weights(table.tasks[train], table.y[train])
        cells: list[ProbeCell] = []
        for layer in dataset.layers:
            features = table.activations[layer]
            c, probe, dev_metric = select_c(
                features[train],
                table.y[train],
                weights,
                features[dev],
                table.y[dev],
                config.probes.c_grid,
                config.probes.max_iterations,
            )
            direction, per_task = difference_in_means(
                features[train], table.y[train], table.tasks[train]
            )
            cosines = pairwise_cosines(per_task)
            values = list(cosines.values())
            mean_cos = round(float(np.mean(values)), 4) if values else None
            min_cos = round(float(np.min(values)), 4) if values else None
            aligned = (
                mean_cos is not None
                and min_cos is not None
                and mean_cos >= config.directions.alignment_min_mean_cosine
                and min_cos >= config.directions.alignment_min_pairwise_cosine
            )
            projections = features @ direction
            centroid_a, centroid_b = task_balanced_centroids(
                projections[train], table.y[train], table.tasks[train]
            )
            direction_path = output_dir / "directions" / f"{state.value}__L{layer:02d}.npy"
            _save_array(direction_path, direction)
            cells.append(
                ProbeCell(
                    layer=layer,
                    selected_c=c,
                    train_rows=int(train.sum()),
                    dev=dev_metric,
                    dev_set1=metric(table.y[dev1], probe.scores(features[dev1])),
                    dev_set2=metric(table.y[dev2], probe.scores(features[dev2])),
                    direction=DirectionEstimate(
                        training_tasks=tuple(sorted(per_task)),
                        pairwise_cosines=cosines,
                        mean_pairwise_cosine=mean_cos,
                        min_pairwise_cosine=min_cos,
                        aligned=aligned,
                        centroid_a=round(centroid_a, 4),
                        centroid_b=round(centroid_b, 4),
                        centroid_gap=round(centroid_b - centroid_a, 4),
                        direction_path=_relative(direction_path, root),
                        direction_sha256=_sha(direction_path.read_bytes()),
                    ),
                    dev_projection_set1=metric(table.y[dev1], projections[dev1]),
                    dev_projection_set2=metric(table.y[dev2], projections[dev2]),
                )
            )
        best_probe = max(cells, key=lambda cell: (cell.dev.auroc or 0.0, -cell.layer))
        aligned_cells = [cell for cell in cells if cell.direction.aligned]
        best_direction = (
            max(
                aligned_cells,
                key=lambda cell: (cell.dev_projection_set2.auroc or 0.0, -cell.layer),
            )
            if aligned_cells
            else None
        )
        if best_direction is None:
            notes.append(
                f"{state.value}: task-level difference vectors do not align at any layer; "
                "no shared policy direction is claimed (VIII.E.7)"
            )
        baselines: list[BaselineFit] = []
        for baseline in TEXT_BASELINES:
            featurizer = TextFeaturizer(baseline, table, train)
            c, _probe, dev_metric = select_c(
                featurizer.features(train),
                table.y[train],
                weights,
                featurizer.features(dev),
                table.y[dev],
                config.probes.c_grid,
                config.probes.max_iterations,
            )
            baselines.append(BaselineFit(baseline=baseline, selected_c=c, dev=dev_metric))
        state_fits.append(
            StateFit(
                state=state,
                cells=tuple(cells),
                probe_selected_layer=best_probe.layer,
                direction_selected_layer=None if best_direction is None else best_direction.layer,
                direction_claim=(
                    "no_shared_direction"
                    if best_direction is None
                    else "shared_direction_candidate"
                ),
                baselines=tuple(baselines),
            )
        )
        probe_layer[state] = best_probe.layer
        probe_c[state] = best_probe.selected_c
        direction_layer[state] = None if best_direction is None else best_direction.layer
        direction_sha[state] = (
            None if best_direction is None else best_direction.direction.direction_sha256
        )
        centroids[state] = (
            None
            if best_direction is None
            else (best_direction.direction.centroid_a, best_direction.direction.centroid_b)
        )
        # Control directions at the probe-selected layer (Stage 4 controls VIII.F.6-8 / IX.F).
        layer = best_probe.layer
        features = table.activations[layer]
        train_all_sets = table.mask(split=SplitName.TRAIN)
        for name, labels in (
            ("paraphrase_set_identity", (table.sets == ParaphraseSet.SET2.value).astype(np.int64)),
            ("lexical_framing", (table.framings == "prohibition").astype(np.int64)),
            (
                "unrelated_fact_plan_format",
                (table.formats == Stage1PlanFormat.FREEFORM.value).astype(np.int64),
            ),
        ):
            try:
                control, _ = difference_in_means(
                    features[train_all_sets], labels[train_all_sets], table.tasks[train_all_sets]
                )
            except Stage3Error:
                continue
            path = output_dir / "directions" / f"{state.value}__L{layer:02d}__{name}.npy"
            _save_array(path, control)
            control_directions[f"{state.value}:{name}"] = _relative(path, root)
        for framing, other in (("prohibition", "permission"), ("permission", "prohibition")):
            framed = table.mask(
                split=SplitName.TRAIN, paraphrase_set=ParaphraseSet.SET1, framing=framing
            )
            try:
                framed_direction, _ = difference_in_means(
                    features[framed], table.y[framed], table.tasks[framed]
                )
            except Stage3Error:
                continue
            path = output_dir / "directions" / f"{state.value}__L{layer:02d}__from_{framing}.npy"
            _save_array(path, framed_direction)
            control_directions[f"{state.value}:from_{framing}_to_{other}"] = _relative(path, root)
        rng = np.random.default_rng(config.directions.random_direction_seed)
        random_direction = rng.standard_normal(dataset.hidden_size).astype(np.float32)
        random_direction /= float(np.linalg.norm(random_direction))
        path = output_dir / "directions" / f"{state.value}__L{layer:02d}__random.npy"
        _save_array(path, random_direction)
        control_directions[
            f"{state.value}:random_seed_{config.directions.random_direction_seed}"
        ] = _relative(path, root)
    r_probe = (
        "skipped: the multiclass applicable-clause-position probe requires "
        f"{config.probes.r_probe_min_train_tasks} training tasks; {len(train_tasks)} available"
        if len(train_tasks) < config.probes.r_probe_min_train_tasks
        else "not implemented in the pilot analysis"
    )
    fit = Stage3ProbeFit(
        created_at=_now(),
        dataset_path=_relative(dataset_path, root),
        dataset_sha256=_sha(dataset_path.read_bytes()),
        train_tasks=train_tasks,
        dev_tasks=dev_tasks,
        c_grid=config.probes.c_grid,
        states=tuple(state_fits),
        r_probe=r_probe,
        notes=tuple(notes),
    )
    fit_path = output_dir / "probes-dev.json"
    _write_model(fit_path, fit)
    selection = Stage3Selection(
        created_at=_now(),
        dataset_path=fit.dataset_path,
        dataset_sha256=fit.dataset_sha256,
        probe_fit_sha256=_sha(fit_path.read_bytes()),
        config_sha256=_sha(config_path.read_bytes()),
        decodable_auroc_min=config.probes.decodable_auroc_min,
        activation_over_text_min_gain=config.probes.activation_over_text_min_gain,
        alignment_min_mean_cosine=config.directions.alignment_min_mean_cosine,
        alignment_min_pairwise_cosine=config.directions.alignment_min_pairwise_cosine,
        strength_multipliers=config.directions.strength_multipliers,
        probe_layer=probe_layer,
        probe_c=probe_c,
        direction_layer=direction_layer,
        direction_sha256=direction_sha,
        centroids=centroids,
        control_directions=control_directions,
    )
    _write_model(output_dir / "selection.json", selection)
    return selection


# --------------------------------------------------------------------------------------------
# Held-out phase (VIII.D.6, VIII.C.7)
# --------------------------------------------------------------------------------------------


class HeldoutStateResult(StrictModel):
    state: BoundaryState
    probe_layer: int
    probe_c: float
    test: Metric
    test_set1: Metric
    test_set2: Metric
    train_set2_transfer: Metric
    per_test_task: dict[str, Metric]
    direction_layer: int | None
    projection_test: Metric | None
    projection_test_set2: Metric | None
    projection_train_set2_transfer: Metric | None
    framing_transfer: dict[str, Metric]
    baselines_test: dict[TextBaseline, Metric]
    best_text_baseline_auroc: float | None
    shuffled_labels_test: Metric
    paraphrase_set_probe_test: Metric
    framing_probe_test: Metric
    surface_only_control: Metric | None
    decodable: bool
    transfers_to_set2: bool
    activations_beat_text: bool
    row_projections: dict[str, float]


class Stage3Heldout(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    selection_sha256: Sha256
    dataset_sha256: Sha256
    test_tasks: tuple[str, ...]
    states: tuple[HeldoutStateResult, ...]


def evaluate_stage3_heldout(
    selection_path: Path, repository_root: Path, output: Path
) -> Stage3Heldout:
    root = repository_root.resolve()
    selection = _load(Stage3Selection, selection_path)
    if output.exists():
        raise Stage3Error(f"held-out results already exist: {output}")
    dataset_path = root / selection.dataset_path
    if _sha(dataset_path.read_bytes()) != selection.dataset_sha256:
        raise Stage3Error("dataset changed after selection was frozen")
    dataset = load_stage3_dataset(dataset_path)
    manifest = load_activation_manifest(root / dataset.activation_manifest_path)
    config_path = root / manifest.config_path
    if _sha(config_path.read_bytes()) != selection.config_sha256:
        raise Stage3Error("Stage 3 config changed after selection was frozen")
    config = load_stage3_config(config_path)
    plans = load_plan_texts(dataset, root)
    test_tasks = dataset.tasks_by_split[SplitName.TEST]
    results: list[HeldoutStateResult] = []
    for state in BoundaryState:
        table = load_state_table(dataset, root, state, config, plans)
        layer = selection.probe_layer[state]
        c = selection.probe_c[state]
        features = table.activations[layer]
        train = table.mask(split=SplitName.TRAIN, paraphrase_set=ParaphraseSet.SET1)
        train2 = table.mask(split=SplitName.TRAIN, paraphrase_set=ParaphraseSet.SET2)
        test = table.mask(split=SplitName.TEST)
        test1 = table.mask(split=SplitName.TEST, paraphrase_set=ParaphraseSet.SET1)
        test2 = table.mask(split=SplitName.TEST, paraphrase_set=ParaphraseSet.SET2)
        weights = task_balanced_weights(table.tasks[train], table.y[train])
        probe = fit_probe(features[train], table.y[train], weights, c, config.probes.max_iterations)
        test_metric = metric(table.y[test], probe.scores(features[test]))
        set2_metric = metric(table.y[test2], probe.scores(features[test2]))
        per_task = {
            task: metric(
                table.y[table.mask(task=task)], probe.scores(features[table.mask(task=task)])
            )
            for task in test_tasks
        }
        # Direction projections.
        direction_layer = selection.direction_layer[state]
        projection_test = projection_test2 = projection_train2 = None
        row_projections: dict[str, float] = {}
        framing_transfer: dict[str, Metric] = {}
        if direction_layer is not None:
            direction_path = _direction_path(selection_path.parent, state, direction_layer)
            direction = np.load(direction_path).astype(np.float32)
            if _sha(direction_path.read_bytes()) != selection.direction_sha256[state]:
                raise Stage3Error("direction file changed after selection")
            dir_features = table.activations[direction_layer]
            projections = dir_features @ direction
            projection_test = metric(table.y[test], projections[test])
            projection_test2 = metric(table.y[test2], projections[test2])
            projection_train2 = metric(table.y[train2], projections[train2])
            row_projections = {
                job_id: round(float(value), 4)
                for job_id, value in zip(table.job_ids, projections, strict=True)
            }
        probe_layer_features = features
        for framing, other in (("prohibition", "permission"), ("permission", "prohibition")):
            key = f"{state.value}:from_{framing}_to_{other}"
            relative = selection.control_directions.get(key)
            if relative is None:
                continue
            framed = np.load(root / relative).astype(np.float32)
            heldout_other = table.mask(framing=other) & (
                table.mask(split=SplitName.TEST) | table.mask(split=SplitName.DEV)
            )
            framing_transfer[f"from_{framing}_to_{other}"] = metric(
                table.y[heldout_other], (probe_layer_features @ framed)[heldout_other]
            )
        # Text and metadata baselines with the identical protocol (C chosen on dev, scored on test).
        dev = table.mask(split=SplitName.DEV)
        baselines_test: dict[TextBaseline, Metric] = {}
        for baseline in TEXT_BASELINES:
            featurizer = TextFeaturizer(baseline, table, train)
            chosen_c, fitted, _dev = select_c(
                featurizer.features(train),
                table.y[train],
                weights,
                featurizer.features(dev),
                table.y[dev],
                config.probes.c_grid,
                config.probes.max_iterations,
            )
            del chosen_c
            baselines_test[baseline] = metric(
                table.y[test], fitted.scores(featurizer.features(test))
            )
        text_aurocs = [m.auroc for m in baselines_test.values() if m.auroc is not None]
        best_text = max(text_aurocs) if text_aurocs else None
        # Controls at the probe layer.
        rng = np.random.default_rng(config.probes.shuffle_seed)
        shuffled = table.y[train].copy()
        for task in np.unique(table.tasks[train]):
            group = np.where(table.tasks[train] == task)[0]
            shuffled[group] = rng.permutation(shuffled[group])
        shuffled_probe = fit_probe(
            features[train], shuffled, weights, c, config.probes.max_iterations
        )
        shuffled_metric = metric(table.y[test], shuffled_probe.scores(features[test]))
        train_all = table.mask(split=SplitName.TRAIN)
        set_labels = (table.sets == ParaphraseSet.SET2.value).astype(np.int64)
        set_probe = fit_probe(
            features[train_all],
            set_labels[train_all],
            task_balanced_weights(table.tasks[train_all], set_labels[train_all]),
            c,
            config.probes.max_iterations,
        )
        set_metric = metric(set_labels[test], set_probe.scores(features[test]))
        framing_labels = (table.framings == "prohibition").astype(np.int64)
        framing_probe = fit_probe(
            features[train_all],
            framing_labels[train_all],
            task_balanced_weights(table.tasks[train_all], framing_labels[train_all]),
            c,
            config.probes.max_iterations,
        )
        framing_metric = metric(framing_labels[test], framing_probe.scores(features[test]))
        surface_control = None
        if state is BoundaryState.RENDERER_INGESTION and dataset.control_rows:
            control_features, control_y = _control_features(dataset, root, layer)
            surface_control = metric(control_y, probe.scores(control_features))
        threshold = selection.decodable_auroc_min
        decodable = test_metric.auroc is not None and test_metric.auroc >= threshold
        transfers = set2_metric.auroc is not None and set2_metric.auroc >= threshold
        beats_text = (
            test_metric.auroc is not None
            and best_text is not None
            and test_metric.auroc - best_text >= selection.activation_over_text_min_gain
        )
        results.append(
            HeldoutStateResult(
                state=state,
                probe_layer=layer,
                probe_c=c,
                test=test_metric,
                test_set1=metric(table.y[test1], probe.scores(features[test1])),
                test_set2=set2_metric,
                train_set2_transfer=metric(table.y[train2], probe.scores(features[train2])),
                per_test_task=per_task,
                direction_layer=direction_layer,
                projection_test=projection_test,
                projection_test_set2=projection_test2,
                projection_train_set2_transfer=projection_train2,
                framing_transfer=framing_transfer,
                baselines_test=baselines_test,
                best_text_baseline_auroc=best_text,
                shuffled_labels_test=shuffled_metric,
                paraphrase_set_probe_test=set_metric,
                framing_probe_test=framing_metric,
                surface_only_control=surface_control,
                decodable=decodable,
                transfers_to_set2=transfers,
                activations_beat_text=beats_text,
                row_projections=row_projections,
            )
        )
    heldout = Stage3Heldout(
        created_at=_now(),
        selection_sha256=_sha(selection_path.read_bytes()),
        dataset_sha256=selection.dataset_sha256,
        test_tasks=test_tasks,
        states=tuple(results),
    )
    _write_model(output, heldout)
    return heldout


def _control_features(dataset: Stage3Dataset, root: Path, layer: int) -> tuple[Floats, Ints]:
    run_directory = (root / dataset.activation_manifest_path).parent
    index = dataset.layers.index(layer)
    features = []
    labels = []
    for row in dataset.control_rows:
        path = run_directory / row.state.path
        if _sha(path.read_bytes()) != row.state.sha256:
            raise Stage3Error(f"control activation changed: {row.state.path}")
        features.append(np.load(path).astype(np.float32)[index])
        labels.append(int(row.label_policy is POSITIVE_POLICY))
    return np.stack(features), np.array(labels, dtype=np.int64)


def _direction_path(analysis_dir: Path, state: BoundaryState, layer: int) -> Path:
    return analysis_dir / "directions" / f"{state.value}__L{layer:02d}.npy"


# --------------------------------------------------------------------------------------------
# Report (VIII.G, VIII.H, XII.C)
# --------------------------------------------------------------------------------------------


class InterpretationRow(StrictModel):
    result: str
    interpretation: str
    evidence: str


class QuadrantProjection(StrictModel):
    quadrant: Quadrant
    rows: int
    mean_projection: float | None
    by_split: dict[SplitName, int]


class Stage3Status(StrictModel):
    stage1_gate: Stage1GateStatus
    stage2_status: Stage2Status
    stage3_status: Literal[
        "valid_continuation", "provisional_pending_stage1", "exploratory_stage1_failed"
    ]


class Stage3Report(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    run_id: str
    design_mode: DesignMode
    pilot: bool
    generalization_claim: str
    dataset_sha256: Sha256
    selection_sha256: Sha256
    heldout_sha256: Sha256
    status: Stage3Status
    label_agreement_reliable: bool
    label_agreement_kappas: dict[str, float | None]
    quadrant_counts: dict[str, int]
    visible_retention_rate: float | None
    clause_selection_correct_rate: float | None
    confident_wrong_clause_rate: float | None
    decodable_by_state: dict[BoundaryState, bool]
    transfers_to_set2_by_state: dict[BoundaryState, bool]
    activations_beat_text_by_state: dict[BoundaryState, bool]
    test_auroc_by_state: dict[BoundaryState, float | None]
    best_text_auroc_by_state: dict[BoundaryState, float | None]
    direction_aligned_by_state: dict[BoundaryState, bool]
    availability_differs_across_boundaries: bool
    quadrant_projections: dict[BoundaryState, tuple[QuadrantProjection, ...]]
    interpretation: tuple[InterpretationRow, ...]
    probe_generalizes: bool
    causal_evaluation_authorized: bool
    stop_or_pivot: str | None
    r_probe: str


def build_stage3_report(
    selection_path: Path, heldout_path: Path, repository_root: Path, output: Path
) -> Stage3Report:
    root = repository_root.resolve()
    if output.exists():
        raise Stage3Error(f"report already exists: {output}")
    selection = _load(Stage3Selection, selection_path)
    heldout = _load(Stage3Heldout, heldout_path)
    if heldout.selection_sha256 != _sha(selection_path.read_bytes()):
        raise Stage3Error("held-out results are bound to another selection")
    dataset_path = root / selection.dataset_path
    if _sha(dataset_path.read_bytes()) != selection.dataset_sha256:
        raise Stage3Error("dataset changed after selection")
    dataset = load_stage3_dataset(dataset_path)
    fit = _load(Stage3ProbeFit, selection_path.parent / "probes-dev.json")
    if _sha((selection_path.parent / "probes-dev.json").read_bytes()) != selection.probe_fit_sha256:
        raise Stage3Error("probe fit changed after selection")
    manifest = load_activation_manifest(root / dataset.activation_manifest_path)
    stage3_config = load_stage3_config(root / manifest.config_path)
    stage2 = load_stage2_config(root / stage3_config.stage2_config_path)
    gate = stage1_gate_status(stage2, root)
    stage2_status = stage2_status_for(gate)
    by_state = {result.state: result for result in heldout.states}
    fits = {state_fit.state: state_fit for state_fit in fit.states}
    labeled = [row for row in dataset.rows if row.policy_visibility is not None]
    visible = _rate([row.visible_policy_retained is True for row in labeled])
    correct = _rate([row.clause_selection is ClauseSelection.CORRECT for row in labeled])
    confident_wrong = _rate(
        [
            row.clause_selection is ClauseSelection.WRONG_CLAUSE
            and row.confidence is not None
            and row.confidence.value == "confident"
            for row in labeled
        ]
    )
    decodable = {state: by_state[state].decodable for state in BoundaryState}
    transfers = {state: by_state[state].transfers_to_set2 for state in BoundaryState}
    beats = {state: by_state[state].activations_beat_text for state in BoundaryState}
    aligned = {
        state: fits[state].direction_claim == "shared_direction_candidate"
        for state in BoundaryState
    }
    availability = decodable[BoundaryState.PLANNER_INPUT] != decodable[
        BoundaryState.PLANNER_OUTPUT
    ] or (decodable[BoundaryState.PLANNER_OUTPUT] != decodable[BoundaryState.RENDERER_INGESTION])
    quadrant_projections = {
        state: _quadrant_projections(dataset, by_state[state].row_projections)
        for state in BoundaryState
    }
    interpretation = _interpret(dataset, by_state, visible, fit.r_probe)
    probe_generalizes = any(decodable[s] and transfers[s] for s in BoundaryState)
    renderer_aligned = aligned[BoundaryState.RENDERER_INGESTION]
    authorized = probe_generalizes and renderer_aligned and dataset.complete
    stop_or_pivot = None
    if not probe_generalizes:
        stop_or_pivot = (
            "probe does not generalize to held-out tasks and paraphrase set 2: report the "
            "negative result; do not patch a cherry-picked direction (XIII.8, VIII.H.4)"
        )
    elif not renderer_aligned:
        stop_or_pivot = (
            "task-level directions do not align at renderer ingestion: report task-specific "
            "results as a case study; no held-out causal evaluation (VIII.E.7)"
        )
    report = Stage3Report(
        created_at=_now(),
        run_id=dataset.run_id,
        design_mode=dataset.design_mode,
        pilot=dataset.pilot,
        generalization_claim=(
            f"none: mechanistic case study on {len(heldout.test_tasks)} held-out base task(s) "
            f"({', '.join(heldout.test_tasks)}); fewer than 12 policy-counterfactual tasks "
            "(XI.I.10)"
        ),
        dataset_sha256=selection.dataset_sha256,
        selection_sha256=_sha(selection_path.read_bytes()),
        heldout_sha256=_sha(heldout_path.read_bytes()),
        status=Stage3Status(
            stage1_gate=gate,
            stage2_status=stage2_status,
            stage3_status=stage2_status,
        ),
        label_agreement_reliable=dataset.agreement.reliable,
        label_agreement_kappas={
            "clause_selection": dataset.agreement.clause_selection_kappa,
            "policy_visibility": dataset.agreement.policy_visibility_kappa,
        },
        quadrant_counts=dataset.quadrant_counts,
        visible_retention_rate=visible,
        clause_selection_correct_rate=correct,
        confident_wrong_clause_rate=confident_wrong,
        decodable_by_state=decodable,
        transfers_to_set2_by_state=transfers,
        activations_beat_text_by_state=beats,
        test_auroc_by_state={s: by_state[s].test.auroc for s in BoundaryState},
        best_text_auroc_by_state={s: by_state[s].best_text_baseline_auroc for s in BoundaryState},
        direction_aligned_by_state=aligned,
        availability_differs_across_boundaries=availability,
        quadrant_projections=quadrant_projections,
        interpretation=interpretation,
        probe_generalizes=probe_generalizes,
        causal_evaluation_authorized=authorized,
        stop_or_pivot=stop_or_pivot,
        r_probe=fit.r_probe,
    )
    _write_model(output, report)
    return report


def _quadrant_projections(
    dataset: Stage3Dataset, projections: dict[str, float]
) -> tuple[QuadrantProjection, ...]:
    out: list[QuadrantProjection] = []
    quadrants: tuple[Quadrant, ...] = (
        "faithful_success",
        "false_certificate",
        "hidden_use",
        "visible_omission_behavioral_failure",
    )
    for quadrant in quadrants:
        rows = [row for row in dataset.rows if row.quadrant == quadrant]
        values = [projections[row.job_id] for row in rows if row.job_id in projections]
        out.append(
            QuadrantProjection(
                quadrant=quadrant,
                rows=len(rows),
                mean_projection=round(float(np.mean(values)), 4) if values else None,
                by_split={split: sum(row.split is split for row in rows) for split in SplitName},
            )
        )
    return tuple(out)


def _interpret(
    dataset: Stage3Dataset,
    by_state: dict[BoundaryState, HeldoutStateResult],
    visible_rate: float | None,
    r_probe: str,
) -> tuple[InterpretationRow, ...]:
    """VIII.G rows selected by the held-out decodability pattern and the visible labels."""
    rows: list[InterpretationRow] = []
    inp = by_state[BoundaryState.PLANNER_INPUT]
    out = by_state[BoundaryState.PLANNER_OUTPUT]
    ing = by_state[BoundaryState.RENDERER_INGESTION]
    test_rows = [r for r in dataset.rows if r.split is SplitName.TEST and r.quadrant is not None]
    wrong_clause = _rate([r.clause_selection is ClauseSelection.WRONG_CLAUSE for r in test_rows])
    if wrong_clause:
        rows.append(
            InterpretationRow(
                result="Plans select the wrong clause on held-out tasks",
                interpretation=(
                    "Cannot separate 'planner failed to identify the applicable clause' from "
                    "'planner represented relevance but failed to externalize it' because the R "
                    f"probe was not run: {r_probe}"
                ),
                evidence=f"wrong_clause rate on held-out plans = {wrong_clause}",
            )
        )
    if not inp.decodable:
        rows.append(
            InterpretationRow(
                result="G is not decodable at planner input",
                interpretation="Planner did not form an accessible representation of G",
                evidence=f"planner_input test AUROC = {inp.test.auroc}",
            )
        )
    elif not out.decodable:
        rows.append(
            InterpretationRow(
                result="G is decodable at planner input but not planner output",
                interpretation=(
                    "G was formed but not retained or externalized in the completed plan"
                ),
                evidence=(
                    f"planner_input AUROC = {inp.test.auroc}; "
                    f"planner_output AUROC = {out.test.auroc}"
                ),
            )
        )
    correct_but_omitted = _rate(
        [
            r.clause_selection is ClauseSelection.CORRECT
            and r.policy_visibility is not PolicyVisibility.PRESERVED
            for r in test_rows
        ]
    )
    if correct_but_omitted and not out.decodable:
        rows.append(
            InterpretationRow(
                result="R is correct but G is absent at planner output",
                interpretation=(
                    "Planner selected the right clause but lost its policy value during compression"
                ),
                evidence=(
                    f"correct-clause-without-preserved-G rate = {correct_but_omitted}; "
                    f"planner_output AUROC = {out.test.auroc}"
                ),
            )
        )
    if visible_rate and visible_rate > 0.5 and not ing.decodable:
        rows.append(
            InterpretationRow(
                result="G is visible in the plan but not decodable at renderer ingestion",
                interpretation="Renderer failed to encode the transmitted distinction",
                evidence=(
                    f"visible retention = {visible_rate}; "
                    f"renderer_ingestion AUROC = {ing.test.auroc}"
                ),
            )
        )
    assigned = _rate([bool(r.behavioral_success) for r in test_rows])
    if ing.decodable and assigned is not None and assigned < 0.5:
        rows.append(
            InterpretationRow(
                result="G is decodable at renderer ingestion but code violates G",
                interpretation="Renderer represents G but does not use it successfully",
                evidence=(
                    f"renderer_ingestion AUROC = {ing.test.auroc}; held-out "
                    f"assigned-and-functional majority rate = {assigned}"
                ),
            )
        )
    for state, result in by_state.items():
        if result.decodable and not result.activations_beat_text:
            rows.append(
                InterpretationRow(
                    result=f"Text predicts G as well as {state.value} activations",
                    interpretation="Activations add no monitorability beyond reading the plan",
                    evidence=(
                        f"probe AUROC = {result.test.auroc}; best text/length baseline AUROC = "
                        f"{result.best_text_baseline_auroc}"
                    ),
                )
            )
    if not rows:
        rows.append(
            InterpretationRow(
                result=(
                    "G is decodable at every boundary, transfers to paraphrase set 2, and "
                    "beats text"
                ),
                interpretation=(
                    "No loss location identified on held-out tasks; the causal stage tests whether "
                    "the renderer-ingestion representation is used"
                ),
                evidence="see decodable_by_state and activations_beat_text_by_state",
            )
        )
    return tuple(rows)


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def _save_array(path: Path, values: Floats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise Stage3Error(f"refusing to overwrite {path}")
    with path.open("xb") as handle:
        np.save(handle, values.astype(np.float32))


def _rate(values: Sequence[bool]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise Stage3Error(f"artifact must live inside the repository: {path}")
    return resolved.relative_to(root).as_posix()


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise Stage3Error(f"cannot load {model.__name__} from {path}: {error}") from error


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_model(path: Path, model: StrictModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise Stage3Error(f"refusing to overwrite {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(model.model_dump_json(indent=2) + "\n")
