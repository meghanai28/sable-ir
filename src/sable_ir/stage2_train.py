"""RTX 5090 QLoRA trainer for the frozen Stage 2 planner dataset."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import random
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from sable_ir.schema import StrictModel
from sable_ir.stage2 import (
    FrozenDatasetRow,
    SplitName,
    Stage2DatasetManifest,
    Stage2Error,
    Stage2TrainingManifest,
    load_stage2_config,
)


class Stage2TrainingResult(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    started_at: str
    finished_at: str
    training_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    adapter_directory: str
    adapter_file_sha256s: dict[str, str]
    trainable_parameter_names_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    trainable_parameters: int
    total_parameters: int
    trainable_fraction: float
    train_rows: int
    dev_rows: int
    status: Literal["awaiting_dev_checkpoint_evaluation"] = (
        "awaiting_dev_checkpoint_evaluation"
    )
    test_split_accessed: Literal[False] = False
    renderer_adapter_enabled: Literal[False] = False


def run_stage2_training(
    manifest_path: Path, repository_root: Path, confirmation: str
) -> Stage2TrainingResult:
    """Train exactly one planner adapter; checkpoint choice remains a later dev-only operation."""
    manifest = Stage2TrainingManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
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
    dataset = Stage2DatasetManifest.model_validate_json(
        dataset_path.read_text(encoding="utf-8")
    )
    train_rows = _load_rows(dataset_path.parent / dataset.files[SplitName.TRAIN].path)
    dev_rows = _load_rows(dataset_path.parent / dataset.files[SplitName.DEV].path)
    if not train_rows or not dev_rows:
        raise Stage2Error("training requires nonempty frozen train and dev files")
    result_path = manifest_path.parent / "training-result.json"
    if result_path.exists():
        raise Stage2Error("this manifest already has a completed training result")
    started_at = _now()
    random.seed(config.qlora.seed)

    try:
        import torch  # type: ignore[import-not-found]
        from datasets import Dataset  # type: ignore[import-not-found]
        from peft import (  # type: ignore[import-not-found]
            LoraConfig,
            get_peft_model,
            prepare_model_for_kbit_training,
        )
        from transformers import (  # type: ignore[import-not-found]
            AutoModelForMultimodalLM,
            AutoProcessor,
            BitsAndBytesConfig,
        )
        from trl import SFTConfig, SFTTrainer  # type: ignore[import-not-found]
    except ImportError as error:
        raise Stage2Error("Stage 2 PC dependencies are not installed") from error

    gpu_matches = (
        torch.cuda.is_available()
        and config.expected_gpu_pattern.lower() in torch.cuda.get_device_name(0).lower()
    )
    if not gpu_matches:
        raise Stage2Error("training is authorized only on the configured RTX 5090 CUDA device")
    torch.manual_seed(config.qlora.seed)
    torch.cuda.manual_seed_all(config.qlora.seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=config.qlora.quant_type,
        bnb_4bit_use_double_quant=config.qlora.double_quant,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    processor = AutoProcessor.from_pretrained(
        manifest.model.model_id,
        revision=manifest.model.revision,
        trust_remote_code=False,
    )
    model = AutoModelForMultimodalLM.from_pretrained(
        manifest.model.model_id,
        revision=manifest.model.revision,
        trust_remote_code=False,
        quantization_config=quantization,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    if model.__class__.__name__ != manifest.model.architecture:
        raise Stage2Error(
            f"pinned model architecture changed: {model.__class__.__name__}"
        )
    model = prepare_model_for_kbit_training(model)
    target_pattern = re.compile(config.qlora.target_modules_regex)
    targets = sorted(
        name for name, _module in model.named_modules() if target_pattern.fullmatch(name)
    )
    if len(targets) < 200 or any("language_model" not in name for name in targets):
        raise Stage2Error(
            f"language-only LoRA target discovery was unsafe ({len(targets)} modules)"
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
    if not trainable_names or any(
        "lora_" not in name or "language_model" not in name for name in trainable_names
    ):
        raise Stage2Error("a non-planner or non-LoRA parameter is trainable")
    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    total = sum(parameter.numel() for parameter in model.parameters())
    output = root / manifest.output_directory
    output.mkdir(parents=True, exist_ok=False)
    tokenizer = processor.tokenizer
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenized_train = _tokenize_rows(
        train_rows, tokenizer, config.qlora.max_sequence_tokens
    )
    tokenized_dev = _tokenize_rows(dev_rows, tokenizer, config.qlora.max_sequence_tokens)
    training_args = SFTConfig(
        output_dir=str(output),
        num_train_epochs=config.qlora.epochs,
        learning_rate=config.qlora.learning_rate,
        per_device_train_batch_size=config.qlora.per_device_train_batch_size,
        per_device_eval_batch_size=config.qlora.per_device_eval_batch_size,
        gradient_accumulation_steps=config.qlora.gradient_accumulation_steps,
        warmup_ratio=config.qlora.warmup_ratio,
        weight_decay=config.qlora.weight_decay,
        seed=config.qlora.seed,
        data_seed=config.qlora.data_seed,
        save_strategy=config.qlora.save_strategy,
        eval_strategy=config.qlora.eval_strategy,
        max_length=config.qlora.max_sequence_tokens,
        completion_only_loss=False,
        packing=False,
        bf16=True,
        tf32=False,
        gradient_checkpointing=True,
        report_to="none",
        load_best_model_at_end=False,
    )
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=Dataset.from_list(tokenized_train),
        eval_dataset=Dataset.from_list(tokenized_dev),
        processing_class=tokenizer,
    )
    trainer.train()
    final_adapter = output / "final-adapter-unselected"
    trainer.save_model(str(final_adapter))
    processor.save_pretrained(str(final_adapter))
    state_path = output / "trainer-state.json"
    _write_new(state_path, json.dumps(trainer.state.to_dict(), indent=2, sort_keys=True) + "\n")
    hashes = _hash_tree(final_adapter)
    names_payload = "\n".join(trainable_names) + "\n"
    _write_new(output / "trainable-parameter-names.txt", names_payload)
    result = Stage2TrainingResult(
        run_id=manifest.run_id,
        started_at=started_at,
        finished_at=_now(),
        training_manifest_sha256=_sha(manifest_path.read_bytes()),
        adapter_directory=os.path.relpath(final_adapter, root),
        adapter_file_sha256s=hashes,
        trainable_parameter_names_sha256=_sha(names_payload.encode()),
        trainable_parameters=trainable,
        total_parameters=total,
        trainable_fraction=trainable / total,
        train_rows=len(train_rows),
        dev_rows=len(dev_rows),
    )
    _write_new(result_path, result.model_dump_json(indent=2) + "\n")
    return result


def _load_rows(path: Path) -> list[FrozenDatasetRow]:
    return [
        FrozenDatasetRow.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _tokenize_rows(
    rows: list[FrozenDatasetRow], tokenizer: Any, max_length: int
) -> list[dict[str, list[int]]]:
    tokenized: list[dict[str, list[int]]] = []
    for row in rows:
        prefix = tokenizer.apply_chat_template(
            [{"role": "user", "content": row.prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        completion = row.completion + tokenizer.eos_token
        prefix_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
        full_ids = tokenizer(prefix + completion, add_special_tokens=False)["input_ids"]
        if len(full_ids) > max_length:
            raise Stage2Error(
                f"reference row {row.row_id} has {len(full_ids)} tokens; truncation is forbidden"
            )
        tokenized.append(
            {
                "input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": [-100] * len(prefix_ids) + full_ids[len(prefix_ids) :],
            }
        )
    return tokenized


def _versions(names: dict[str, str]) -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in names}


def _hash_tree(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): _sha(path.read_bytes())
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_new(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
