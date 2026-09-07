from pathlib import Path

from resume_experiment import latest_matching_checkpoint, next_seed_path, read_checkpoint


def test_resume_selection_requires_exact_prefix(tmp_path: Path) -> None:
    # Given
    prefix = "env-incre-model_k=1_range_0_user-model"
    expected = tmp_path / f"{prefix}_20260901000000.jsonl"
    expected.write_text("")
    unrelated = tmp_path / f"other-{prefix}_20260902000000.jsonl"
    unrelated.write_text("")
    (tmp_path / "usage.jsonl").write_text("")
    # When
    selected = latest_matching_checkpoint(tmp_path, prefix)
    # Then
    assert selected == expected


def test_resume_reads_latest_revision_within_source(tmp_path: Path) -> None:
    # Given
    checkpoint = tmp_path / "checkpoint.jsonl"
    checkpoint.write_text(
        '{"sample_id":"same","reward":null}\n'
        '{"sample_id":"same","reward":0,"retry_exhausted":true}\n'
    )
    # When
    records = read_checkpoint(checkpoint)
    # Then
    assert len(records) == 1
    assert '"retry_exhausted":true' in records[0].payload


def test_resume_orders_second_and_microsecond_names_chronologically(
    tmp_path: Path,
) -> None:
    # Given
    prefix = "env-incre-model_k=1_range_0_user-model"
    older = tmp_path / f"{prefix}_20260901000000123456.jsonl"
    newer = tmp_path / f"{prefix}_20260902000000.jsonl"
    older.write_text("")
    newer.write_text("")
    # When / Then
    assert latest_matching_checkpoint(tmp_path, prefix) == newer


def test_seed_name_uses_runtime_microsecond_precision(tmp_path: Path) -> None:
    # Given / When
    seed = next_seed_path(tmp_path, "prefix")
    # Then
    timestamp = seed.stem.rpartition("_")[2]
    assert timestamp.isdigit()
    assert len(timestamp) == 20
