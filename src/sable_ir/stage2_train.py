"""Single-GPU QLoRA trainer for the frozen Stage 2 planner dataset (Windows RTX 5080, 16 GiB).

The base model is loaded through the official multimodal auto class in NF4, every parameter is
frozen, and exactly one LoRA adapter is attached to language-model linear modules. The vision
tower, embeddings, and norms are never trainable. Per-epoch adapter checkpoints are written so a
dev-only behavioral selection can happen afterwards; nothing here reads the test split.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import Field

from sable_ir.config import load_task
from sable_ir.schema import PolicyValue, Stage1Concision, Stage1PlanFormat, StrictModel
from sable_ir.stage2 import (
    FrozenDatasetRow,
    SplitName,
    Stage2Config,
    Stage2DatasetManifest,
    Stage2Error,
    Stage2ModelCanaryRecord,
    Stage2ModelSpec,
    Stage2TrainingManifest,
    build_stage2_planner_prompt,
    canary_path_for,
    gpu_identity,
    load_frozen_rows,
    load_stage2_config,
    package_versions,
    render_safety_document,
    validate_dataset_files,
)

MINIMUM_LANGUAGE_TARGETS = 64


class ChatTokenizer(Protocol):
    """The subset of a Hugging Face tokenizer that the masking code depends on."""

    eos_token: str
    pad_token_id: int | None

    def apply_chat_template(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...

    def __call__(self, text: str, **kwargs: Any) -> Any: ...


class CheckpointRecord(StrictModel):
    directory: str
    global_step: int
    epoch: float | None
    adapter_file_sha256s: dict[str, str]


class Stage2TrainingResult(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    started_at: str
    finished_at: str
    training_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_id: str
    revision: str
    architecture: str
    checkpoints: tuple[CheckpointRecord, ...]
    final_adapter_directory: str
    final_adapter_file_sha256s: dict[str, str]
    trainable_parameter_names_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    lora_target_module_count: int
    trainable_parameters: int
    total_parameters: int
    trainable_fraction: float
    train_rows: int
    dev_rows: int
    max_train_sequence_tokens: int
    train_log_history: tuple[dict[str, float], ...]
    peak_gpu_memory_gib: float | None
    status: Literal["awaiting_dev_checkpoint_selection"] = "awaiting_dev_checkpoint_selection"
    test_split_accessed: Literal[False] = False
    renderer_adapter_enabled: Literal[False] = False


def tokenize_rows(
    rows: Sequence[FrozenDatasetRow], tokenizer: ChatTokenizer, max_length: int
) -> list[dict[str, list[int]]]:
    """Non-thinking chat prefix is masked with -100; only the reference plan receives loss."""
    tokenized: list[dict[str, list[int]]] = []
    for row in rows:
        prefix = tokenizer.apply_chat_template(
            [{"role": "user", "content": row.prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        completion = row.completion.rstrip("\n") + tokenizer.eos_token
        prefix_ids = list(tokenizer(prefix, add_special_tokens=False)["input_ids"])
        full_ids = list(tokenizer(prefix + completion, add_special_tokens=False)["input_ids"])
        if full_ids[: len(prefix_ids)] != prefix_ids:
            raise Stage2Error(f"prefix tokenization is not a prefix of the full row: {row.row_id}")
        if len(full_ids) > max_length:
            raise Stage2Error(
                f"reference row {row.row_id} has {len(full_ids)} tokens; truncation is forbidden"
            )
        if len(full_ids) == len(prefix_ids):
            raise Stage2Error(f"reference row {row.row_id} has an empty completion")
        tokenized.append(
            {
                "input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": [-100] * len(prefix_ids) + full_ids[len(prefix_ids) :],
            }
        )
    return tokenized


def pad_batch(
    features: Sequence[dict[str, list[int]]], pad_token_id: int
) -> dict[str, list[list[int]]]:
    """Right-pad to the longest row; padded positions are ignored by attention and loss."""
    longest = max(len(item["input_ids"]) for item in features)
    batch: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": [], "labels": []}
    for item in features:
        missing = longest - len(item["input_ids"])
        batch["input_ids"].append(item["input_ids"] + [pad_token_id] * missing)
        batch["attention_mask"].append(item["attention_mask"] + [0] * missing)
        batch["labels"].append(item["labels"] + [-100] * missing)
    return batch


def select_lora_targets(module_names: Sequence[str], pattern: str) -> list[str]:
    """Return language-model linear modules matching the frozen regex; refuse anything else."""
    compiled = re.compile(pattern)
    targets = sorted(name for name in module_names if compiled.fullmatch(name))
    if len(targets) < MINIMUM_LANGUAGE_TARGETS:
        raise Stage2Error(
            f"language-only LoRA target discovery matched only {len(targets)} modules"
        )
    outside = [name for name in targets if "language_model" not in name]
    if outside:
        raise Stage2Error(f"LoRA targets escaped the language model: {outside[:3]}")
    if any(".visual." in name or name.startswith("visual") for name in targets):
        raise Stage2Error("LoRA targets include the vision tower")
    return targets


def assert_only_language_lora_trainable(trainable_names: Sequence[str]) -> None:
    if not trainable_names:
        raise Stage2Error("no trainable parameters were created")
    bad = [name for name in trainable_names if "lora_" not in name or "language_model" not in name]
    if bad:
        raise Stage2Error(f"a non-planner or non-LoRA parameter is trainable: {bad[:3]}")


def load_quantized_model(
    config: Stage2Config, model_spec: Stage2ModelSpec, *, purpose: str
) -> tuple[Any, Any]:
    """NF4 base through the official multimodal auto class, on the authorized GPU only."""
    try:
        import torch
        from transformers import AutoModelForMultimodalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as error:
        raise Stage2Error("Stage 2 PC dependencies are not installed") from error
    if not torch.cuda.is_available():
        raise Stage2Error(f"{purpose} requires a CUDA device")
    device_name = torch.cuda.get_device_name(0)
    if config.hardware.expected_gpu_pattern.lower() not in device_name.lower():
        raise Stage2Error(
            f"{purpose} is authorized only on {config.hardware.expected_gpu_pattern}: {device_name}"
        )
    model_id = model_spec.active_model_id
    revision = model_spec.active_revision
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        revision=revision,
        trust_remote_code=False,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=config.qlora.quant_type,
            bnb_4bit_use_double_quant=config.qlora.double_quant,
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        device_map={"": 0},
        dtype=torch.bfloat16,
    )
    if model.__class__.__name__ != model_spec.architecture:
        raise Stage2Error(f"pinned model architecture changed: {model.__class__.__name__}")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer, model


def attach_planner_lora(model: Any, config: Stage2Config) -> tuple[Any, list[str], list[str]]:
    """Freeze everything, attach one language-model-only LoRA, and verify the trainable set."""
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    targets = select_lora_targets(
        [name for name, _module in model.named_modules()], config.qlora.target_modules_regex
    )
    lora = LoraConfig(
        r=config.qlora.lora_rank,
        lora_alpha=config.qlora.lora_alpha,
        lora_dropout=config.qlora.lora_dropout,
        target_modules=targets,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    trainable_names = sorted(
        name for name, parameter in model.named_parameters() if parameter.requires_grad
    )
    assert_only_language_lora_trainable(trainable_names)
    return model, targets, trainable_names


def run_stage2_model_canary(config_path: Path, repository_root: Path) -> Stage2ModelCanaryRecord:
    """Prove the active model fits: NF4 load, one full-length masked training step, generation.

    This is an implementation check for the 16 GiB budget, not an experiment. It is required by
    preflight for whichever model is active, and it is the gate on which the 9B fallback remains
    conditional. A failed attempt is still recorded so the failure is auditable.
    """
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    destination = canary_path_for(config, root)
    if destination.exists():
        raise Stage2Error(f"canary already recorded: {destination}")
    try:
        import torch
    except ImportError as error:
        raise Stage2Error("Stage 2 PC dependencies are not installed") from error
    versions = package_versions()
    created_at = _now()
    base_record: dict[str, Any] = {
        "created_at": created_at,
        "config_sha256": _sha(config_path.read_bytes()),
        "model_id": config.model.active_model_id,
        "revision": config.model.active_revision,
        "architecture": config.model.architecture,
        "gpu_name": gpu_identity().name,
        "package_versions": versions,
        "max_sequence_tokens": config.qlora.max_sequence_tokens,
    }
    try:
        torch.manual_seed(config.qlora.seed)
        torch.cuda.reset_peak_memory_stats()
        tokenizer, model = load_quantized_model(config, config.model, purpose="model canary")
        model, targets, trainable_names = attach_planner_lora(model, config)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # One optimizer step on a worst-case-length masked row (prefix masked, filler completion).
        spec = load_task(root / config.task_paths[0])
        prompt = build_stage2_planner_prompt(
            spec.surface_request,
            render_safety_document(spec.documents[PolicyValue.A].clauses),
            Stage1PlanFormat.STRUCTURED,
            Stage1Concision.FULL,
        )
        prefix = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        prefix_ids = list(tokenizer(prefix, add_special_tokens=False)["input_ids"])
        filler_ids = list(
            tokenizer(
                "GUARD: validate the untrusted input before the sink and preserve the policy. ",
                add_special_tokens=False,
            )["input_ids"]
        )
        length = config.qlora.max_sequence_tokens
        if len(prefix_ids) >= length - 8:
            raise Stage2Error("canary prompt alone exceeds max_sequence_tokens")
        completion_ids: list[int] = []
        while len(prefix_ids) + len(completion_ids) < length:
            completion_ids.extend(filler_ids)
        completion_ids = completion_ids[: length - len(prefix_ids)]
        input_ids = torch.tensor([prefix_ids + completion_ids], dtype=torch.long, device="cuda")
        labels = torch.tensor(
            [[-100] * len(prefix_ids) + completion_ids], dtype=torch.long, device="cuda"
        )
        attention = torch.ones_like(input_ids)
        model.train()
        optimizer = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad], lr=config.qlora.learning_rate
        )
        outputs = model(input_ids=input_ids, attention_mask=attention, labels=labels)
        loss_value = float(outputs.loss.detach().float().item())
        outputs.loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        del outputs, optimizer

        # Generation with the adapter enabled (planner) and disabled (renderer).
        model.eval()
        model.config.use_cache = True
        short = tokenizer(prefix, return_tensors="pt", add_special_tokens=False).to("cuda")
        eos_ids = [int(tokenizer.eos_token_id)]
        with torch.inference_mode():
            enabled = model.generate(
                **short,
                do_sample=False,
                max_new_tokens=32,
                eos_token_id=eos_ids,
                pad_token_id=int(tokenizer.pad_token_id),
            )
        with torch.inference_mode(), model.disable_adapter():
            disabled = model.generate(
                **short,
                do_sample=False,
                max_new_tokens=32,
                eos_token_id=eos_ids,
                pad_token_id=int(tokenizer.pad_token_id),
            )
        enabled_new = enabled[0, short["input_ids"].shape[1] :].tolist()
        disabled_new = disabled[0, short["input_ids"].shape[1] :].tolist()
        finish: Literal["stop", "length"] = (
            "stop" if enabled_new and int(enabled_new[-1]) in eos_ids else "length"
        )
        record = Stage2ModelCanaryRecord(
            **base_record,
            lora_target_module_count=len(targets),
            trainable_parameters=trainable,
            training_step_loss=loss_value,
            generation_output_tokens=len(enabled_new),
            generation_finish_reason=finish,
            adapter_disabled_generation_output_tokens=len(disabled_new),
            peak_gpu_memory_gib=round(torch.cuda.max_memory_allocated() / 1024**3, 3),
            passed=True,
        )
        del trainable_names
    except Exception as error:  # noqa: BLE001 - any failure (OOM, API mismatch) is recorded
        record = Stage2ModelCanaryRecord(
            **base_record,
            lora_target_module_count=0,
            trainable_parameters=0,
            training_step_loss=0.0,
            generation_output_tokens=0,
            generation_finish_reason="length",
            adapter_disabled_generation_output_tokens=0,
            peak_gpu_memory_gib=round(torch.cuda.max_memory_allocated() / 1024**3, 3)
            if torch.cuda.is_available()
            else 0.0,
            passed=False,
            error=f"{type(error).__name__}: {error}",
        )
    _write_new(destination, record.model_dump_json(indent=2) + "\n")
    return record


def run_stage2_training(
    manifest_path: Path, repository_root: Path, confirmation: str
) -> Stage2TrainingResult:
    """Train exactly one planner adapter; checkpoint choice remains a later dev-only operation."""
    manifest = Stage2TrainingManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if confirmation != manifest.run_id:
        raise Stage2Error("training confirmation must exactly equal the frozen run ID")
    root = repository_root.resolve()
    if _sha((root / manifest.config_path).read_bytes()) != manifest.config_sha256:
        raise Stage2Error("Stage 2 config changed after the training manifest was frozen")
    dataset_path = root / manifest.dataset_manifest_path
    if _sha(dataset_path.read_bytes()) != manifest.dataset_manifest_sha256:
        raise Stage2Error("Stage 2 dataset manifest changed after authorization")
    current_versions = _versions(manifest.package_versions)
    if current_versions != manifest.package_versions:
        raise Stage2Error(
            f"Stage 2 package versions changed: frozen={manifest.package_versions}, "
            f"current={current_versions}"
        )
    config = load_stage2_config(root / manifest.config_path)
    dataset = Stage2DatasetManifest.model_validate_json(dataset_path.read_text(encoding="utf-8"))
    validate_dataset_files(dataset, dataset_path.parent)
    train_rows = load_frozen_rows(dataset_path.parent / dataset.files[SplitName.TRAIN].path)
    dev_rows = load_frozen_rows(dataset_path.parent / dataset.files[SplitName.DEV].path)
    if not train_rows or not dev_rows:
        raise Stage2Error("training requires nonempty frozen train and dev files")
    result_path = manifest_path.parent / "training-result.json"
    if result_path.exists():
        raise Stage2Error("this manifest already has a completed training result")
    output = root / manifest.output_directory
    if output.exists():
        raise Stage2Error(f"checkpoint directory already exists: {output}")
    started_at = _now()

    try:
        import torch
        from transformers import Trainer, TrainingArguments
    except ImportError as error:
        raise Stage2Error("Stage 2 PC dependencies are not installed") from error

    canary_path = root / manifest.model_canary_path
    if _sha(canary_path.read_bytes()) != manifest.model_canary_sha256:
        raise Stage2Error("model canary changed after authorization")

    torch.manual_seed(config.qlora.seed)
    torch.cuda.manual_seed_all(config.qlora.seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    model_id = manifest.model.active_model_id
    revision = manifest.model.active_revision
    tokenizer, model = load_quantized_model(config, manifest.model, purpose="training")
    architecture = model.__class__.__name__
    model, targets, trainable_names = attach_planner_lora(model, config)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    pad_token_id = int(tokenizer.pad_token_id)
    tokenized_train = tokenize_rows(train_rows, tokenizer, config.qlora.max_sequence_tokens)
    tokenized_dev = tokenize_rows(dev_rows, tokenizer, config.qlora.max_sequence_tokens)
    longest = max(len(item["input_ids"]) for item in tokenized_train + tokenized_dev)

    def collate(features: list[dict[str, list[int]]]) -> dict[str, Any]:
        padded = pad_batch(features, pad_token_id)
        return {key: torch.tensor(value, dtype=torch.long) for key, value in padded.items()}

    output.mkdir(parents=True, exist_ok=False)
    training_args = TrainingArguments(
        output_dir=str(output),
        num_train_epochs=config.qlora.epochs,
        learning_rate=config.qlora.learning_rate,
        per_device_train_batch_size=config.qlora.per_device_train_batch_size,
        per_device_eval_batch_size=config.qlora.per_device_eval_batch_size,
        gradient_accumulation_steps=config.qlora.gradient_accumulation_steps,
        warmup_ratio=config.qlora.warmup_ratio,
        weight_decay=config.qlora.weight_decay,
        lr_scheduler_type="cosine",
        seed=config.qlora.seed,
        data_seed=config.qlora.data_seed,
        save_strategy=config.qlora.save_strategy,
        eval_strategy=config.qlora.eval_strategy,
        save_total_limit=None,
        logging_strategy="steps",
        logging_steps=1,
        bf16=True,
        tf32=False,
        optim=config.qlora.optimizer,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        remove_unused_columns=False,
        report_to="none",
        load_best_model_at_end=False,
        dataloader_num_workers=0,
        group_by_length=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=_ListDataset(tokenized_train),
        eval_dataset=_ListDataset(tokenized_dev),
        data_collator=collate,
        processing_class=tokenizer,
    )
    torch.cuda.reset_peak_memory_stats()
    trainer.train()
    peak_gib = round(torch.cuda.max_memory_allocated() / 1024**3, 3)

    final_adapter = output / "final-adapter-unselected"
    trainer.save_model(str(final_adapter))
    tokenizer.save_pretrained(str(final_adapter))
    state_path = output / "trainer-state.json"
    _write_new(state_path, json.dumps(trainer.state.to_dict(), indent=2, sort_keys=True) + "\n")
    names_payload = "\n".join(trainable_names) + "\n"
    _write_new(output / "trainable-parameter-names.txt", names_payload)
    _write_new(output / "lora-target-modules.txt", "\n".join(targets) + "\n")

    checkpoints = _collect_checkpoints(output, root)
    result = Stage2TrainingResult(
        run_id=manifest.run_id,
        started_at=started_at,
        finished_at=_now(),
        training_manifest_sha256=_sha(manifest_path.read_bytes()),
        model_id=model_id,
        revision=revision,
        architecture=architecture,
        checkpoints=tuple(checkpoints),
        final_adapter_directory=_relative(final_adapter, root),
        final_adapter_file_sha256s=hash_tree(final_adapter),
        trainable_parameter_names_sha256=_sha(names_payload.encode("utf-8")),
        lora_target_module_count=len(targets),
        trainable_parameters=trainable,
        total_parameters=total,
        trainable_fraction=trainable / total,
        train_rows=len(train_rows),
        dev_rows=len(dev_rows),
        max_train_sequence_tokens=longest,
        train_log_history=tuple(
            {k: float(v) for k, v in entry.items() if isinstance(v, int | float)}
            for entry in trainer.state.log_history
        ),
        peak_gpu_memory_gib=peak_gib,
    )
    _write_new(result_path, result.model_dump_json(indent=2) + "\n")
    return result


class _ListDataset:
    def __init__(self, rows: list[dict[str, list[int]]]) -> None:
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self._rows[index]


def _collect_checkpoints(output: Path, root: Path) -> list[CheckpointRecord]:
    records: list[CheckpointRecord] = []
    for directory in sorted(output.glob("checkpoint-*")):
        if not directory.is_dir():
            continue
        step = int(directory.name.split("-")[-1])
        epoch: float | None = None
        state_file = directory / "trainer_state.json"
        if state_file.is_file():
            try:
                epoch_value = json.loads(state_file.read_text(encoding="utf-8")).get("epoch")
                epoch = float(epoch_value) if epoch_value is not None else None
            except (json.JSONDecodeError, TypeError, ValueError):
                epoch = None
        records.append(
            CheckpointRecord(
                directory=_relative(directory, root),
                global_step=step,
                epoch=epoch,
                adapter_file_sha256s=hash_tree(directory, adapter_only=True),
            )
        )
    if not records:
        raise Stage2Error("training produced no per-epoch checkpoints")
    return records


def hash_tree(directory: Path, *, adapter_only: bool = False) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if adapter_only and not path.name.startswith("adapter_"):
            continue
        hashes[path.relative_to(directory).as_posix()] = _sha(path.read_bytes())
    return hashes


def _versions(names: dict[str, str]) -> dict[str, str]:
    current: dict[str, str] = {}
    for name in names:
        try:
            current[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            current[name] = "absent"
    return current


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_new(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
