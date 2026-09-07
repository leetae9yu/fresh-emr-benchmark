import json
from pathlib import Path

import pytest

from metric import calculate_metrics, load_result_file
from src.types import CostInfo, EnvInfo, EnvRunResult, RewardInfo, Task


def outcome(task_id: str, reward: float | None, sample_id: str) -> EnvRunResult:
    task = Task(
        db_id="mimic_iv",
        task_type="incre",
        task_id=task_id,
        instruction="Count records.",
        gold_sql="SELECT 1",
        gold_answer=[[1]],
    )
    return EnvRunResult(
        db_id=task.db_id,
        task_type=task.task_type,
        task_id=task_id,
        sample_id=sample_id,
        reward=reward,
        info=EnvInfo(task=task, reward_info=RewardInfo(reward=reward)),
        messages=[],
        cost=CostInfo(agent_cost=0.2, user_cost=0.1, eval_cost=0.1, total_cost=0.4),
    )


def test_metrics_reject_task_with_only_invalid_attempts() -> None:
    # Given
    results = [outcome("0", 1.0, "valid"), outcome("1", None, "invalid")]
    # When / Then
    with pytest.raises(ValueError):
        calculate_metrics(results, num_trials=1)


def test_metrics_reject_wholly_missing_expected_task() -> None:
    # Given
    expected = {("mimic_iv", "incre", "0"), ("mimic_iv", "incre", "1")}
    # When / Then
    with pytest.raises(ValueError):
        calculate_metrics(
            [outcome("0", 1.0, "valid")], num_trials=1, expected_tasks=expected
        )


def test_metrics_count_invalid_attempt_cost_once() -> None:
    # Given
    invalid = outcome("0", None, "invalid")
    revision = invalid.model_copy(update={"retry_exhausted": True})
    results = [invalid, revision, outcome("0", 1.0, "valid")]
    # When
    metrics = calculate_metrics(results, num_trials=1)
    # Then
    assert metrics["costs"]["total"] == pytest.approx(0.8)
    assert metrics["total_attempts"] == 2
    assert metrics["invalid_attempts"] == 1


def test_metrics_count_latest_sample_revision_once() -> None:
    # Given
    first = outcome("0", None, "same-sample")
    completed = first.model_copy(update={"reward": 1.0})
    # When
    metrics = calculate_metrics([first, completed], num_trials=1)
    # Then
    assert metrics["total_trajectories"] == 1
    assert metrics["costs"]["total"] == pytest.approx(0.4)


def test_metrics_report_unknown_cost_instead_of_complete_zero() -> None:
    # Given
    result = outcome("0", 0.0, "unknown")
    result.cost = CostInfo()
    # When
    metrics = calculate_metrics([result], num_trials=1)
    # Then
    assert metrics["costs"]["missing_total"] == 1
    assert metrics["costs"]["complete"] is False


def test_metrics_reject_empty_cohort_explicitly() -> None:
    # Given / When / Then
    with pytest.raises(ValueError):
        calculate_metrics([], num_trials=1)


def test_result_loader_deduplicates_appended_revisions(tmp_path: Path) -> None:
    # Given
    original = outcome("0", None, "same-sample")
    updated = original.model_copy(update={"reward": 0.0})
    path = tmp_path / "results.jsonl"
    path.write_text(
        "\n".join(json.dumps(row.model_dump()) for row in [original, updated]) + "\n"
    )
    # When
    loaded = load_result_file(str(path))
    # Then
    assert len(loaded) == 1
    assert loaded[0].reward == 0.0


def test_metrics_reject_two_successes_for_same_trial_slot() -> None:
    # Given
    first = outcome("0", 1.0, "first").model_copy(update={"trial_id": 1})
    duplicate = outcome("0", 1.0, "duplicate").model_copy(update={"trial_id": 1})
    # When / Then
    with pytest.raises(ValueError):
        calculate_metrics([first, duplicate], num_trials=2)


def test_metrics_reject_mixed_indexed_and_legacy_trials() -> None:
    # Given
    indexed = outcome("0", 1.0, "indexed").model_copy(update={"trial_id": 1})
    legacy = outcome("0", 1.0, "legacy")
    # When / Then
    with pytest.raises(ValueError):
        calculate_metrics([indexed, legacy], num_trials=2)
