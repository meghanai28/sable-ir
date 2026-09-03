"""GPU runtime for Stage 4 renderer-ingestion interventions.

The pure contracts and report logic live in :mod:`sable_ir.stage4`. This module imports torch and
numpy only inside runtime paths, so configuration/audit commands remain usable on the Mac. The
renderer always runs with the planner adapter disabled.
"""

from __future__ import annotations

import contextlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sable_ir.schema import PolicyValue
from sable_ir.stage1 import build_renderer_prompt
from sable_ir.stage2 import load_stage2_config
from sable_ir.stage2_local import (
    GenerationStatus,
    LocalGeneration,
    Role,
    TransformersLocalGenerator,
    extract_python,
)
from sable_ir.stage3 import BoundaryState, Stage3Dataset, _find_decoder_blocks, load_stage3_dataset
from sable_ir.stage4 import (
    DirectionArtifact,
    DirectionKind,
    DivergenceSpec,
    DivergenceTask,
    FullRunJob,
    SanityPairResult,
    Stage4DirectionSet,
    Stage4Error,
    Stage4ExperimentManifest,
    Stage4FullRunManifest,
    Stage4GenerationRecord,
    _load,
    _sha,
    _write_model,
    load_stage4_config,
)


@dataclass
class PatchTelemetry:
    applied: bool = False
    edited_positions: int = 0
    projection_before: float | None = None
    projection_after: float | None = None
    edit_l2_norm: float | None = None
    orthogonal_component_changed_max_abs: float | None = None


def materialize_stage4_directions(
    experiment_manifest_path: Path,
    repository_root: Path,
    output: Path,
) -> Stage4DirectionSet:
    """Resolve directions needing selected-row or fresh renderer-ingestion activations."""
    import numpy as np

    root = repository_root.resolve()
    experiment = _load(Stage4ExperimentManifest, experiment_manifest_path)
    config = load_stage4_config(root / experiment.config_path)
    dataset_path = root / config.stage3_dataset_path
    if _sha(dataset_path.read_bytes()) != experiment.stage3_dataset_sha256:
        raise Stage4Error("Stage 3 dataset changed after the Stage 4 experiment was frozen")
    dataset = load_stage3_dataset(dataset_path)
    activation_manifest_path = root / experiment.stage3_activation_manifest_path
    if _sha(activation_manifest_path.read_bytes()) != experiment.stage3_activation_manifest_sha256:
        raise Stage4Error("Stage 3 activation manifest changed after Stage 4 preparation")
    activation_run = activation_manifest_path.parent
    selected = experiment.selected_layer
    target = _artifact(experiment.direction_artifacts, DirectionKind.POLICY_ORIENTATION)
    target_vector = _load_vector(root, target)

    artifacts = list(experiment.direction_artifacts)
    test = next(row for row in experiment.recipients if row.split.value == "test")
    dev = next(row for row in experiment.recipients if row.split.value == "dev")

    # Full-vector positive control: the complete held-out source-state A/B displacement. It is
    # normalized only for matched edit strength; unlike the primary projection it may alter any
    # component of the residual stream.
    test_a = _row_state(dataset, activation_run, test.explicit_a.job_id, selected)
    test_b = _row_state(dataset, activation_run, test.explicit_b.job_id, selected)
    full = _unit(test_b - test_a)
    if float(full @ target_vector) < 0:
        full = -full
    full_path = output.parent / "directions" / "full_vector_same_task.npy"
    _save_array(full_path, full)
    artifacts = _replace_artifact(
        artifacts,
        DirectionArtifact(
            kind=DirectionKind.FULL_VECTOR_SAME_TASK,
            layer=selected,
            path=_relative(full_path, root),
            sha256=_sha(full_path.read_bytes()),
            derivation="normalized held-out explicit-B minus explicit-A renderer state",
        ),
    )

    # Unrelated-task target values use the same target direction but scalars from the development
    # task. This is distinct from the train-task centroids used by the primary interchange.
    dev_a = _row_state(dataset, activation_run, dev.explicit_a.job_id, selected)
    dev_b = _row_state(dataset, activation_run, dev.explicit_b.job_id, selected)
    unrelated_value = DirectionArtifact(
        kind=DirectionKind.UNRELATED_TASK_VALUE,
        layer=selected,
        path=target.path,
        sha256=target.sha256,
        derivation="target direction with explicit development-task source projections",
        centroids=(round(float(dev_a @ target_vector), 6), round(float(dev_b @ target_vector), 6)),
    )
    artifacts = _replace_artifact(artifacts, unrelated_value)

    # The unrelated-security direction is a fresh paired capture using the identical held-out
    # omitted plan and two frozen authentication-session statements inserted before END_PLAN.
    stage2_path = root / experiment.stage2_config_path
    if _sha(stage2_path.read_bytes()) != experiment.stage2_config_sha256:
        raise Stage4Error("Stage 2 config changed after Stage 4 preparation")
    capturer = _renderer_capturer(experiment, root, (selected,))
    prompt_a = build_renderer_prompt(
        _surface_request(experiment, root, test.task_id),
        _insert_before_end_plan(test.omitted.plan, experiment.unrelated_security_fact_a),
    )
    prompt_b = build_renderer_prompt(
        _surface_request(experiment, root, test.task_id),
        _insert_before_end_plan(test.omitted.plan, experiment.unrelated_security_fact_b),
    )
    state_a = capturer.capture_renderer_ingestion(prompt_a)
    state_b = capturer.capture_renderer_ingestion(prompt_b)
    if state_a is None or state_b is None:
        raise Stage4Error("unrelated-security control capture did not find END_PLAN")
    unrelated = _unit(
        np.asarray(state_b.values[0], dtype=np.float32)
        - np.asarray(state_a.values[0], dtype=np.float32)
    )
    unrelated_path = output.parent / "directions" / "unrelated_security_fact.npy"
    _save_array(unrelated_path, unrelated)
    artifacts = _replace_artifact(
        artifacts,
        DirectionArtifact(
            kind=DirectionKind.UNRELATED_SECURITY_FACT,
            layer=selected,
            path=_relative(unrelated_path, root),
            sha256=_sha(unrelated_path.read_bytes()),
            derivation=(
                "normalized paired authentication-session fact capture on identical omitted plan"
            ),
        ),
    )

    random = _load_vector(root, _artifact(tuple(artifacts), DirectionKind.RANDOM_ORTHOGONAL))
    result = Stage4DirectionSet(
        created_at=_now(),
        experiment_manifest_sha256=_sha(experiment_manifest_path.read_bytes()),
        artifacts=tuple(artifacts),
        target_random_absolute_dot=round(abs(float(target_vector @ random)), 10),
    )
    _write_model(output, result)
    return result


def run_stage4_sanity(
    experiment_manifest_path: Path,
    direction_set_path: Path,
    repository_root: Path,
    output_directory: Path,
) -> tuple[SanityPairResult, ...]:
    """Run development-only next-token and teacher-forced checks before full code sampling."""
    import numpy as np

    root = repository_root.resolve()
    experiment = _load(Stage4ExperimentManifest, experiment_manifest_path)
    directions = _load(Stage4DirectionSet, direction_set_path)
    if directions.experiment_manifest_sha256 != _sha(experiment_manifest_path.read_bytes()):
        raise Stage4Error("direction set references another Stage 4 experiment")
    config = load_stage4_config(root / experiment.config_path)
    spec = DivergenceSpec.model_validate_json(
        (root / config.divergence_spec_path).read_text(encoding="utf-8")
    )
    divergence_spec_sha = _sha((root / config.divergence_spec_path).read_bytes())
    recipient = next(row for row in experiment.recipients if row.split.value == "dev")
    divergence = spec.tasks.get(recipient.task_id)
    if divergence is None:
        raise Stage4Error(f"no frozen divergence specification for {recipient.task_id}")
    prompt = build_renderer_prompt(
        _surface_request(experiment, root, recipient.task_id), recipient.omitted.plan
    )
    engine = InterventionEngine(experiment, directions, root)
    unpatched = engine.next_logits(prompt, None, None, 1.0)
    unpatched_probs = _softmax(unpatched)
    rows: list[SanityPairResult] = []
    required = (
        DirectionKind.POLICY_ORIENTATION,
        DirectionKind.RANDOM_ORTHOGONAL,
        DirectionKind.LEXICAL_FRAMING,
    )
    for strength in experiment.strength_multipliers:
        for kind in required:
            logits_a = engine.next_logits(prompt, kind, PolicyValue.A, strength)
            logits_b = engine.next_logits(prompt, kind, PolicyValue.B, strength)
            probs_a = _softmax(logits_a)
            probs_b = _softmax(logits_b)
            logodds_a = engine.continuation_log_odds(
                prompt, divergence, kind, PolicyValue.A, strength
            )
            logodds_b = engine.continuation_log_odds(
                prompt, divergence, kind, PolicyValue.B, strength
            )
            token_changes = {
                token: round(
                    engine.token_logit(logits_a, token) - engine.token_logit(logits_b, token),
                    6,
                )
                for token in divergence.policy_relevant_tokens
            }
            raw_path = output_directory / (
                f"{kind.value}__strength_{str(strength).replace('.', '_')}__distributions.npz"
            )
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with raw_path.open("xb") as handle:
                np.savez_compressed(
                    handle,
                    unpatched_logits=unpatched,
                    policy_a_logits=logits_a,
                    policy_b_logits=logits_b,
                )
            result = SanityPairResult(
                run_id=experiment.run_id,
                experiment_manifest_sha256=_sha(experiment_manifest_path.read_bytes()),
                direction_set_sha256=_sha(direction_set_path.read_bytes()),
                divergence_spec_sha256=divergence_spec_sha,
                prompt_sha256=_sha(prompt.encode()),
                task_id=recipient.task_id,
                direction_kind=kind,
                strength_multiplier=strength,
                unpatched_to_a_kl=_kl(probs_a, unpatched_probs),
                unpatched_to_b_kl=_kl(probs_b, unpatched_probs),
                a_vs_b_js_divergence=_js(probs_a, probs_b),
                teacher_forced_a_minus_b_log_odds_gap=round(logodds_a - logodds_b, 6),
                policy_relevant_token_logit_changes=token_changes,
                raw_distribution_path=_relative(raw_path, root),
                raw_distribution_sha256=_sha(raw_path.read_bytes()),
            )
            result_path = raw_path.with_name(
                raw_path.name.replace("distributions.npz", "result.json")
            )
            _write_model(result_path, result)
            rows.append(result)
    return tuple(rows)


def run_stage4_full(
    manifest_path: Path,
    repository_root: Path,
    *,
    limit: int | None = None,
) -> int:
    """Resumably generate the frozen full-run matrix; existing results are never overwritten."""
    root = repository_root.resolve()
    manifest = _load(Stage4FullRunManifest, manifest_path)
    experiment_path = root / manifest.experiment_manifest_path
    if _sha(experiment_path.read_bytes()) != manifest.experiment_manifest_sha256:
        raise Stage4Error("experiment manifest changed after full-run preparation")
    direction_path = root / manifest.direction_set_path
    if _sha(direction_path.read_bytes()) != manifest.direction_set_sha256:
        raise Stage4Error("direction set changed after full-run preparation")
    experiment = _load(Stage4ExperimentManifest, experiment_path)
    directions = _load(Stage4DirectionSet, direction_path)
    if directions.artifacts != manifest.resolved_direction_artifacts:
        raise Stage4Error("full-run directions differ from its frozen manifest")
    engine = InterventionEngine(experiment, directions, root)
    directory = manifest_path.resolve().parent
    completed = 0
    for job in manifest.jobs:
        result_path = directory / job.result_path
        if result_path.exists():
            continue
        if limit is not None and completed >= limit:
            break
        if _sha(job.prompt.encode()) != job.prompt_sha256:
            raise Stage4Error(f"prompt hash mismatch: {job.job_id}")
        generation, telemetry, direction_sha = engine.generate(job)
        raw_path = directory / f"jobs/{job.job_id}/raw.txt"
        _write_text(raw_path, generation.text)
        source: str | None = None
        extraction: str | None = None
        error: str | None = None
        if generation.finish_reason == "length":
            status = GenerationStatus.LENGTH
            error = "renderer hit max_new_tokens"
        else:
            try:
                source, extraction = extract_python(generation.text)
                status = GenerationStatus.GENERATED
            except Exception as failure:
                status = GenerationStatus.MALFORMED
                error = str(failure)
        candidate_sha = None
        if source is not None:
            candidate = directory / job.candidate_path
            _write_text(candidate, source)
            candidate_sha = _sha(candidate.read_bytes())
        record = Stage4GenerationRecord(
            job_id=job.job_id,
            prompt_sha256=job.prompt_sha256,
            generation=generation,
            status=status,
            raw_text_sha256=_sha(generation.text.encode()),
            candidate_sha256=candidate_sha,
            extraction=extraction,
            error=error,
            intervention_applied=telemetry.applied,
            edited_positions=telemetry.edited_positions,
            orthogonal_component_changed_max_abs=(telemetry.orthogonal_component_changed_max_abs),
            direction_sha256=direction_sha,
            projection_before=telemetry.projection_before,
            projection_after=telemetry.projection_after,
            edit_l2_norm=telemetry.edit_l2_norm,
        )
        _write_model(result_path, record)
        completed += 1
    return completed


class InterventionEngine:
    """One loaded frozen base renderer with auditable residual-stream edit hooks."""

    def __init__(
        self,
        experiment: Stage4ExperimentManifest,
        directions: Stage4DirectionSet,
        root: Path,
    ) -> None:
        import numpy as np

        stage2_path = root / experiment.stage2_config_path
        if _sha(stage2_path.read_bytes()) != experiment.stage2_config_sha256:
            raise Stage4Error("Stage 2 configuration hash mismatch")
        config = load_stage2_config(stage2_path)
        adapter = root / experiment.planner_adapter.directory
        self.generator = TransformersLocalGenerator(
            config,
            adapter,
            expected_adapter_hashes=experiment.planner_adapter.adapter_file_sha256s,
        )
        self.torch = self.generator._torch
        self.model = self.generator._model
        self.tokenizer = self.generator._tokenizer
        activation_manifest = _load_activation_manifest(experiment, root)
        self.blocks = _find_decoder_blocks(self.model, activation_manifest.expected_num_layers)
        self.generation_config = config.generation
        self.artifacts = {row.kind: row for row in directions.artifacts}
        self.vectors = {
            kind: np.asarray(_load_vector(root, artifact), dtype=np.float32)
            for kind, artifact in self.artifacts.items()
        }

    def generate(self, job: FullRunJob) -> tuple[LocalGeneration, PatchTelemetry, str | None]:
        if job.direction_kind is None:
            started = time.monotonic()
            generation = self.generator.generate(
                job.prompt,
                role=Role.RENDERER,
                max_new_tokens=self.generation_config.renderer_max_new_tokens,
                seed=job.seed,
            )
            del started
            return generation, PatchTelemetry(applied=False, edited_positions=0), None
        if job.target_policy is None:
            raise Stage4Error("patched full-run job lacks a target policy")
        artifact = self.artifacts[job.direction_kind]
        telemetry = PatchTelemetry(applied=False, edited_positions=0)
        with self._patch(
            job.prompt,
            job.direction_kind,
            job.target_policy,
            job.strength_multiplier,
            telemetry,
        ):
            generation = self.generator.generate(
                job.prompt,
                role=Role.RENDERER,
                max_new_tokens=self.generation_config.renderer_max_new_tokens,
                seed=job.seed,
            )
        if not telemetry.applied or telemetry.edited_positions != 1:
            raise Stage4Error(f"single-position intervention did not apply once: {job.job_id}")
        if (
            job.direction_kind is DirectionKind.POLICY_ORIENTATION
            and (telemetry.orthogonal_component_changed_max_abs or 0.0) > 1e-5
        ):
            raise Stage4Error(f"primary edit changed an orthogonal component: {job.job_id}")
        return generation, telemetry, artifact.sha256

    def next_logits(
        self,
        prompt: str,
        kind: DirectionKind | None,
        policy: PolicyValue | None,
        strength: float,
    ) -> Any:
        import numpy as np

        encoded, _text = self._encode(prompt)
        telemetry = PatchTelemetry(applied=False, edited_positions=0)
        patch = (
            contextlib.nullcontext()
            if kind is None
            else self._patch(prompt, kind, _required_policy(policy), strength, telemetry)
        )
        with self.torch.inference_mode(), self.model.disable_adapter(), patch:
            output = self.model(**encoded, use_cache=False)
        if kind is not None and not telemetry.applied:
            raise Stage4Error("sanity intervention hook did not apply")
        return np.asarray(output.logits[0, -1].detach().to(self.torch.float32).cpu().numpy())

    def continuation_log_odds(
        self,
        prompt: str,
        spec: DivergenceTask,
        kind: DirectionKind,
        policy: PolicyValue,
        strength: float,
    ) -> float:
        a = self._continuation_log_probability(
            prompt, spec.common_code_prefix, spec.policy_a_continuation, kind, policy, strength
        )
        b = self._continuation_log_probability(
            prompt, spec.common_code_prefix, spec.policy_b_continuation, kind, policy, strength
        )
        return a - b

    def token_logit(self, logits: Any, text: str) -> float:
        ids = self.tokenizer(text, add_special_tokens=False)["input_ids"]
        if not ids:
            raise Stage4Error(f"policy token has no tokenization: {text!r}")
        return float(logits[int(ids[0])])

    def _continuation_log_probability(
        self,
        prompt: str,
        prefix: str,
        continuation: str,
        kind: DirectionKind,
        policy: PolicyValue,
        strength: float,
    ) -> float:
        torch = self.torch
        templated = self._templated(prompt)
        prefix_ids = self.tokenizer(
            templated + prefix, add_special_tokens=False, return_tensors="pt"
        )["input_ids"]
        continuation_ids = self.tokenizer(
            continuation, add_special_tokens=False, return_tensors="pt"
        )["input_ids"]
        input_ids = torch.cat((prefix_ids, continuation_ids), dim=1).to(self.model.device)
        encoded = {"input_ids": input_ids, "attention_mask": torch.ones_like(input_ids)}
        telemetry = PatchTelemetry(applied=False, edited_positions=0)
        with (
            torch.inference_mode(),
            self.model.disable_adapter(),
            self._patch(
                prompt,
                kind,
                policy,
                strength,
                telemetry,
                full_text=templated + prefix + continuation,
            ),
        ):
            logits = self.model(**encoded, use_cache=False).logits
        start = int(prefix_ids.shape[1]) - 1
        predicted = logits[0, start : start + continuation_ids.shape[1], :]
        log_probs = torch.log_softmax(predicted.to(torch.float32), dim=-1)
        selected = log_probs.gather(1, continuation_ids[0].unsqueeze(1)).sum()
        return float(selected.detach().cpu())

    def _patch(
        self,
        prompt: str,
        kind: DirectionKind,
        policy: PolicyValue,
        strength: float,
        telemetry: PatchTelemetry,
        *,
        full_text: str | None = None,
    ) -> contextlib.AbstractContextManager[None]:
        vector = self.vectors[kind]
        artifact = self.artifacts[kind]
        target = self.artifacts[DirectionKind.POLICY_ORIENTATION]
        target_vector = self.vectors[DirectionKind.POLICY_ORIENTATION]
        templated = self._templated(prompt)
        position = self._end_plan_position(full_text or templated, templated)
        block = self.blocks[artifact.layer]
        torch = self.torch

        def hook(_module: Any, _inputs: Any, output: Any) -> Any:
            hidden = output[0] if isinstance(output, tuple) else output
            if telemetry.applied or hidden.shape[1] <= position:
                return output
            changed = hidden.clone()
            current = changed[0, position, :]
            direction = torch.as_tensor(vector, device=current.device, dtype=current.dtype)
            target_direction = torch.as_tensor(
                target_vector, device=current.device, dtype=current.dtype
            )
            before = torch.dot(current.to(torch.float32), direction.to(torch.float32))
            target_before = torch.dot(current.to(torch.float32), target_direction.to(torch.float32))
            if kind in (
                DirectionKind.POLICY_ORIENTATION,
                DirectionKind.UNRELATED_TASK_VALUE,
                DirectionKind.PREREGISTERED_EARLY_LAYER,
            ):
                if artifact.centroids is None:
                    raise Stage4Error(f"{kind.value} lacks frozen scalar centroids")
                desired = artifact.centroids[0 if policy is PolicyValue.A else 1]
                delta_scalar = strength * (desired - float(before))
            else:
                if target.centroids is None:
                    raise Stage4Error("primary direction lacks training-task centroids")
                desired_target = target.centroids[0 if policy is PolicyValue.A else 1]
                matched_norm = abs(strength * (desired_target - float(target_before)))
                sign = -1.0 if policy is PolicyValue.A else 1.0
                delta_scalar = sign * matched_norm
            delta = delta_scalar * direction
            changed[0, position, :] = current + delta
            after = before + delta_scalar
            residual = delta.to(torch.float32) - torch.dot(
                delta.to(torch.float32), direction.to(torch.float32)
            ) * direction.to(torch.float32)
            telemetry.applied = True
            telemetry.edited_positions = 1
            telemetry.projection_before = round(float(before), 6)
            telemetry.projection_after = round(float(after), 6)
            telemetry.edit_l2_norm = round(float(torch.linalg.vector_norm(delta)), 6)
            telemetry.orthogonal_component_changed_max_abs = round(float(residual.abs().max()), 10)
            if isinstance(output, tuple):
                return (changed, *output[1:])
            return changed

        handle = block.register_forward_hook(hook)

        @contextlib.contextmanager
        def registered() -> Any:
            try:
                yield
            finally:
                handle.remove()

        return registered()

    def _templated(self, prompt: str) -> str:
        return str(
            self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        )

    def _encode(self, prompt: str) -> tuple[dict[str, Any], str]:
        text = self._templated(prompt)
        encoded = self.tokenizer(text, return_tensors="pt", add_special_tokens=False)
        return ({key: value.to(self.model.device) for key, value in encoded.items()}, text)

    def _end_plan_position(self, text: str, templated_prompt: str) -> int:
        marker = templated_prompt.rfind("END_PLAN")
        if marker < 0:
            raise Stage4Error("renderer prompt has no END_PLAN marker")
        char_end = marker + len("END_PLAN")
        encoded = self.tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
        for index, (start, end) in enumerate(encoded["offset_mapping"]):
            if start < end and start <= char_end - 1 < end:
                return index
        raise Stage4Error("could not locate the END_PLAN token")


def _renderer_capturer(
    experiment: Stage4ExperimentManifest, root: Path, layers: tuple[int, ...]
) -> Any:
    from sable_ir.stage3 import TransformersActivationCapturer

    config = load_stage2_config(root / experiment.stage2_config_path)
    activation_manifest = _load_activation_manifest(experiment, root)
    return TransformersActivationCapturer(
        config,
        root / experiment.planner_adapter.directory,
        expected_adapter_hashes=experiment.planner_adapter.adapter_file_sha256s,
        layers=layers,
        expected_num_layers=activation_manifest.expected_num_layers,
        hidden_size=activation_manifest.hidden_size,
    )


def _load_activation_manifest(experiment: Stage4ExperimentManifest, root: Path) -> Any:
    from sable_ir.stage3 import load_activation_manifest

    path = root / experiment.stage3_activation_manifest_path
    return load_activation_manifest(path)


def _row_state(dataset: Stage3Dataset, run_directory: Path, job_id: str, layer: int) -> Any:
    import numpy as np

    row = next((item for item in dataset.rows if item.job_id == job_id), None)
    if row is None:
        raise Stage4Error(f"selected Stage 3 row is missing: {job_id}")
    state = row.states.get(BoundaryState.RENDERER_INGESTION)
    if state is None:
        raise Stage4Error(f"selected row lacks renderer-ingestion state: {job_id}")
    path = run_directory / state.path
    if _sha(path.read_bytes()) != state.sha256:
        raise Stage4Error(f"selected activation changed: {job_id}")
    values = np.load(path).astype(np.float32)
    try:
        index = dataset.layers.index(layer)
    except ValueError as error:
        raise Stage4Error(f"layer {layer} was not captured") from error
    return values[index]


def _surface_request(experiment: Stage4ExperimentManifest, root: Path, task_id: str) -> str:
    from sable_ir.config import load_task

    stage2 = load_stage2_config(root / experiment.stage2_config_path)
    for path in stage2.task_paths:
        task = load_task(root / path)
        if task.id == task_id:
            return task.surface_request
    raise Stage4Error(f"task is absent from Stage 2 config: {task_id}")


def _insert_before_end_plan(plan: str, fact: str) -> str:
    marker = plan.rfind("END_PLAN")
    if marker < 0:
        raise Stage4Error("selected recipient has no END_PLAN marker")
    return f"{plan[:marker].rstrip()}\n\nUnrelated control fact: {fact}\nEND_PLAN"


def _artifact(artifacts: tuple[DirectionArtifact, ...], kind: DirectionKind) -> DirectionArtifact:
    matches = [row for row in artifacts if row.kind is kind]
    if len(matches) != 1:
        raise Stage4Error(f"expected one {kind.value} direction artifact")
    return matches[0]


def _replace_artifact(
    artifacts: list[DirectionArtifact], replacement: DirectionArtifact
) -> list[DirectionArtifact]:
    return [replacement if row.kind is replacement.kind else row for row in artifacts]


def _load_vector(root: Path, artifact: DirectionArtifact) -> Any:
    import numpy as np

    if artifact.path is None or artifact.sha256 is None:
        raise Stage4Error(f"direction is not materialized: {artifact.kind.value}")
    path = root / artifact.path
    if _sha(path.read_bytes()) != artifact.sha256:
        raise Stage4Error(f"direction hash mismatch: {artifact.kind.value}")
    return _unit(np.load(path).astype(np.float32))


def _unit(vector: Any) -> Any:
    import numpy as np

    norm = float(np.linalg.norm(vector))
    if not norm or not np.isfinite(norm):
        raise Stage4Error("cannot normalize a zero or non-finite direction")
    return np.asarray(vector / norm, dtype=np.float32)


def _save_array(path: Path, values: Any) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        np.save(handle, np.asarray(values, dtype=np.float32))


def _softmax(logits: Any) -> Any:
    import numpy as np

    shifted = logits.astype(np.float64) - float(np.max(logits))
    values = np.exp(shifted)
    return values / values.sum()


def _kl(p: Any, q: Any) -> float:
    import numpy as np

    floor = 1e-12
    return round(float(np.sum(p * (np.log(p + floor) - np.log(q + floor)))), 8)


def _js(p: Any, q: Any) -> float:
    midpoint = (p + q) / 2
    return round((_kl(p, midpoint) + _kl(q, midpoint)) / 2, 8)


def _required_policy(policy: PolicyValue | None) -> PolicyValue:
    if policy is None:
        raise Stage4Error("patched distribution call requires a target policy")
    return policy


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise Stage4Error(f"artifact must live inside repository: {path}")
    return resolved.relative_to(root).as_posix()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise Stage4Error(f"refusing to overwrite {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds")
