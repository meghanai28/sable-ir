from pathlib import Path

from sable_ir.config import load_task
from sable_ir.prompts import (
    CODE_OUTPUT_INSTRUCTION,
    CWEVAL_DIRECT_PROMPT,
    build_task_prompt,
    build_wire_prompt,
)
from sable_ir.schema import Stage0Condition


def test_prompt_views_do_not_expose_gold_clause_ids() -> None:
    task = load_task(Path("tasks/path_symlink_report/task.json"))
    full = build_task_prompt(task, Stage0Condition.FULL_DOCUMENT_A)
    relevant = build_task_prompt(task, Stage0Condition.RELEVANT_CLAUSE_ONLY_A)
    surface = build_task_prompt(task, Stage0Condition.SURFACE_ONLY_DIRECT)

    applicable = task.documents["A"].applicable_clauses[0].text
    distractor = task.documents["A"].clauses[1].text
    assert applicable in full
    assert distractor in full
    assert applicable in relevant
    assert distractor not in relevant
    assert applicable not in surface
    assert "filesystem_links" not in full


def test_every_wire_prompt_gets_identical_code_only_wrapper() -> None:
    task = load_task(Path("tasks/sql_identifier/task.json"))

    for condition in Stage0Condition:
        prompt = build_wire_prompt(task, condition)
        if condition is Stage0Condition.ORIGINAL_BENCHMARK:
            assert prompt == CWEVAL_DIRECT_PROMPT.format(
                code_prompt=task.original_benchmark.code_prompt.strip()
            )
        else:
            assert prompt.startswith(CODE_OUTPUT_INSTRUCTION)
