"""Loading helpers that preserve the repository root as the path boundary."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from pydantic import ValidationError

from sable_ir.schema import Stage0Config, Stage1Config, TaskSpec


class ConfigLoadError(ValueError):
    """A configuration or task file could not be read or validated."""


def load_stage0_config(path: Path) -> Stage0Config:
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
        return Stage0Config.model_validate(data)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise ConfigLoadError(f"could not load Stage 0 config {path}: {error}") from error


def load_stage1_config(path: Path) -> Stage1Config:
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
        return Stage1Config.model_validate(data)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise ConfigLoadError(f"could not load Stage 1 config {path}: {error}") from error


def load_task(path: Path) -> TaskSpec:
    try:
        with path.open(encoding="utf-8") as task_file:
            data = json.load(task_file)
        return TaskSpec.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ConfigLoadError(f"could not load task {path}: {error}") from error
