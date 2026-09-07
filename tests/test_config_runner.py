"""Config launcher contracts, exercised through real subprocesses without APIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from experiment_runner import Plan, Summary

LAUNCHER = Path(__file__).resolve().parents[1] / "experiment_runner.py"
OPTIONS = {
    "env": "",
    "task_type": "",
    "model": "",
    "embedding_model": "",
    "api_base": "",
    "agent_strategy": "",
    "temperature": "float",
    "user_model": "",
    "user_temperature": "float",
    "user_strategy": "",
    "result_dir": "",
    "num_trials": "int",
    "max_concurrency": "int",
    "task_ids": "ids",
    "max_agent_turns": "int",
    "max_retry": "int",
    "timeout": "int",
    "validation_model": "",
    "validation_trials": "int",
    "tool_mode": "",
    "metadata_access": "",
    "failure_feedback": "",
    "schema_guidance": "",
    "reward_scope": "",
    "trial_id": "int",
    "reasoning_effort": "",
    "max_completion_tokens": "int",
    "verbose": "flag",
}


@pytest.fixture
def experiment(tmp_path: Path) -> Path:
    source = tmp_path / "checkout"
    source.mkdir()
    declarations: list[str] = []
    for name, kind in OPTIONS.items():
        extra = {
            "int": ", type=int",
            "float": ", type=float",
            "ids": ", type=int, nargs='+'",
            "flag": ", action='store_true'",
        }.get(kind, "")
        declarations.append(f"p.add_argument('--{name}'{extra})")
    _ = (source / "run.py").write_text(
        "import argparse,json,os,signal,subprocess,sys\nfrom pathlib import Path\n"
        + "p=argparse.ArgumentParser()\n"
        + "\n".join(declarations)
        + "\n"
        + "a=p.parse_args()\n"
        + "out=Path(a.result_dir); out.mkdir(parents=True,exist_ok=True)\n"
        + "mode=os.environ.get('FAKE_MODE','complete')\n"
        + "if mode=='timeout':\n"
        + " child=subprocess.Popen([sys.executable,'-c','import signal; signal.pause()'])\n"
        + " (out/'child.pid').write_text(str(child.pid))\n"
        + " signal.pause()\n"
        + "with (out/f'{a.env}-{a.task_type}-fake_k=1_range_ids_user-fake_20260101000000.jsonl').open('a') as f:\n"
        + " for tid in a.task_ids:\n"
        + "  if mode=='missing' and tid==a.task_ids[-1]: continue\n"
        + "  row=dict(db_id=a.env,task_type=a.task_type,task_id=str(tid),"
        + "trial_id=getattr(a,'trial_id',None),sample_id=f'{tid}-sample',reward=0.0)\n"
        + "  if mode=='wrong_trial': row['trial_id']=999\n"
        + "  if mode=='wrong_db': row['db_id']='eicu_star'\n"
        + "  if mode=='null': row['reward']=None\n"
        + "  f.write(json.dumps(row)+'\\n')\n"
        + "  if mode=='duplicate':\n"
        + "   row['sample_id']+='-duplicate'; f.write(json.dumps(row)+'\\n')\n"
        + "print('fake runner completed',flush=True)\n"
        + "sys.exit(7 if mode=='nonzero' else 0)\n"
    )
    for env in ("mimic_iv_star", "eicu_star"):
        folder = source / "src" / "envs" / env
        folder.mkdir(parents=True)
        for flow in ("incre", "adapt"):
            _ = (folder / f"eval_{flow}.jsonl").write_text(
                json.dumps(
                    [
                        {"task_id": str(i), "db_id": env, "task_type": flow}
                        for i in range(4)
                    ]
                )
            )
    config = tmp_path / "pilot.toml"
    _ = config.write_text(f"""name = "pilot"
envs = ["mimic_iv_star"]
task_types = ["incre"]
trials = 2
result_root = "output"

[source]
path = "checkout"
python = {json.dumps(sys.executable)}

[defaults]
embedding_model = "openrouter/openai/text-embedding-3-small"
run_timeout = 2

[user]
model = "openrouter/test/user"
temperature = 0.7
strategy = "nested-reflection"

[validator]
model = "openrouter/test/validator"
trials = 1

[[models]]
name = "agent"
model = "openrouter/test/agent"
temperature = 0.0

[[conditions]]
name = "full"
tool_mode = "full"

[task_ids.mimic_iv_star]
incre = [0, 2]
""")
    return config


def launch(
    config: Path, *args: str, mode: str = "complete"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(LAUNCHER), str(config), *args],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={
            **os.environ,
            "FAKE_MODE": mode,
            "OPENROUTER_API_KEY": "never-save-this-secret",
        },
    )


def test_cli_exists_before_implementation() -> None:
    # Given / When: the deliverable's real CLI is requested.
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    # Then
    assert result.returncode == 0, result.stderr


def test_dry_run_is_write_free_and_expands_stable_trials(experiment: Path) -> None:
    # Given
    before = {
        p.relative_to(experiment.parent): p.stat().st_mtime_ns
        for p in experiment.parent.rglob("*")
    }
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode == 0, result.stderr
    plan = Plan.model_validate_json(result.stdout)
    assert len(plan.jobs) == 2
    assert [j.trial_id for j in plan.jobs] == [1, 2]
    assert plan.expected_tasks == 4
    for job in plan.jobs:
        command = job.command
        assert command[command.index("--num_trials") + 1] == "1"
        assert command[command.index("--trial_id") + 1] == str(job.trial_id)
        assert command[command.index("--schema_guidance") + 1] == "benchmark"
    assert "never-save-this-secret" not in result.stdout
    assert before == {
        p.relative_to(experiment.parent): p.stat().st_mtime_ns
        for p in experiment.parent.rglob("*")
    }


def test_cartesian_and_database_flow_specific_ids(experiment: Path) -> None:
    # Given
    text = experiment.read_text().replace(
        'envs = ["mimic_iv_star"]', 'envs = ["mimic_iv_star", "eicu"]'
    )
    text = text.replace('task_types = ["incre"]', 'task_types = ["incre", "adapt"]')
    _ = experiment.write_text(
        text
        + """adapt = [1]
[task_ids.eicu]
incre = [3]
adapt = [0, 1]
[[models]]
name = "other"
model = "openrouter/test/other"
temperature = 0.5
[[conditions]]
name = "schema_removed"
tool_mode = "schema_removed"
"""
    )
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode == 0, result.stderr
    plan = Plan.model_validate_json(result.stdout)
    assert len(plan.jobs) == 32
    assert plan.expected_tasks == 48
    assert {
        tuple(j.task_ids)
        for j in plan.jobs
        if j.env == "eicu" and j.task_type == "incre"
    } == {(3,)}
    assert {
        j.schema_guidance for j in plan.jobs if j.condition == "schema_removed"
    } == {"identifier_free"}


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("temperature = 0.0", "temperature = 0.2"),
        ("trials = 2", "trials = 3"),
        ("run_timeout = 2", "run_timeout = 3"),
        ("incre = [0, 2]", "incre = [1, 2]"),
    ],
)
def test_resolved_config_changes_identity(experiment: Path, old: str, new: str) -> None:
    # Given
    first = Plan.model_validate_json(launch(experiment, "--dry-run").stdout)
    _ = experiment.write_text(experiment.read_text().replace(old, new))
    # When
    second = Plan.model_validate_json(launch(experiment, "--dry-run").stdout)
    # Then
    assert first.config_hash != second.config_hash
    assert first.result_dir != second.result_dir


def test_dirty_source_changes_identity_but_results_do_not(experiment: Path) -> None:
    # Given
    first = Plan.model_validate_json(launch(experiment, "--dry-run").stdout)
    runner = experiment.parent / "checkout" / "run.py"
    _ = runner.write_text(runner.read_text() + "\n# source change\n")
    # When
    second = Plan.model_validate_json(launch(experiment, "--dry-run").stdout)
    # Then
    assert first.config_hash != second.config_hash
    out = experiment.parent / "checkout" / "results"
    out.mkdir()
    _ = (out / "old.jsonl").write_text("secret output")
    assert (
        Plan.model_validate_json(launch(experiment, "--dry-run").stdout).config_hash
        == second.config_hash
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("incre = [0, 2]", "incre = [4]"),
        ("incre = [0, 2]", "incre = [0, 0]"),
        ("incre = [0, 2]", "adapt = [0]"),
        ("run_timeout = 2", "run_timeout = 0"),
        ("run_timeout = 2", 'run_timeout = 2\napi_key = "secret"'),
        ("temperature = 0.0", 'temperature = "0.0"'),
        (
            "run_timeout = 2",
            'run_timeout = 2\napi_base = "https://user:secret@host/v1"',
        ),
    ],
)
def test_invalid_settings_fail_before_writes(
    experiment: Path, old: str, new: str
) -> None:
    # Given
    _ = experiment.write_text(experiment.read_text().replace(old, new))
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode != 0
    assert not (experiment.parent / "output").exists()
    assert "secret" not in result.stderr


def test_requested_unsupported_setting_is_rejected(experiment: Path) -> None:
    # Given
    runner = experiment.parent / "checkout" / "run.py"
    _ = runner.write_text(
        runner.read_text().replace("p.add_argument('--reasoning_effort')", "")
    )
    _ = experiment.write_text(
        experiment.read_text().replace(
            "temperature = 0.0", 'temperature = 0.0\nreasoning_effort = "low"'
        )
    )
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode != 0
    assert "reasoning_effort" in result.stderr


def test_old_checkout_uses_manifest_trial_identity(experiment: Path) -> None:
    # Given
    runner = experiment.parent / "checkout" / "run.py"
    _ = runner.write_text(
        runner.read_text().replace("p.add_argument('--trial_id', type=int)", "")
    )
    # When
    result = launch(experiment)
    # Then
    assert result.returncode == 0, result.stderr
    summary = Summary.model_validate_json(result.stdout)
    manifest = Plan.model_validate_json(
        (Path(summary.result_dir) / "manifest.json").read_text()
    )
    assert all("--trial_id" not in j.command for j in manifest.jobs)
    assert [j.trial_id for j in manifest.jobs] == [1, 2]
    assert summary.completed_tasks == 4


def test_execution_and_resume_check_real_coverage(experiment: Path) -> None:
    # Given
    first = launch(experiment)
    assert first.returncode == 0, first.stderr
    summary = Summary.model_validate_json(first.stdout)
    root = Path(summary.result_dir)
    checkpoint_times = {p: p.stat().st_mtime_ns for p in root.rglob("*.jsonl")}
    # When
    resumed = launch(experiment, "--resume")
    # Then
    assert resumed.returncode == 0, resumed.stderr
    assert Summary.model_validate_json(resumed.stdout).completed_tasks == 4
    assert checkpoint_times == {p: p.stat().st_mtime_ns for p in root.rglob("*.jsonl")}
    assert len(list((root / "logs").glob("*.log"))) == 2
    assert len(list((root / "jobs").glob("*.json"))) == 2
    assert "never-save-this-secret" not in (root / "manifest.json").read_text()
    assert launch(experiment).returncode != 0


@pytest.mark.parametrize(
    "mode", ["missing", "null", "duplicate", "wrong_trial", "wrong_db", "nonzero"]
)
def test_exit_zero_is_not_completion(experiment: Path, mode: str) -> None:
    # Given / When
    result = launch(experiment, mode=mode)
    # Then
    assert result.returncode == 1, result.stderr
    summary = Summary.model_validate_json(result.stdout)
    assert summary.complete is False
    assert summary.expected_tasks == 4


def test_timeout_kills_and_reaps_process_tree(experiment: Path) -> None:
    # Given: elapsed time is the behavior under test; the child blocks on a signal.
    _ = experiment.write_text(
        experiment.read_text().replace("trials = 2", "trials = 1")
    )
    # When
    result = launch(experiment, mode="timeout")
    # Then
    assert result.returncode == 1, result.stderr
    summary = Summary.model_validate_json(result.stdout)
    assert summary.jobs[0].timed_out is True
    pid = int(next(Path(summary.result_dir).rglob("child.pid")).read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("selection", ["", "task_ids = {}\n"])
def test_omitted_or_empty_selection_resolves_full_catalog(
    experiment: Path, selection: str
) -> None:
    # Given
    text = experiment.read_text().split("[task_ids.mimic_iv_star]")[0]
    _ = experiment.write_text(selection + text)
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode == 0, result.stderr
    plan = Plan.model_validate_json(result.stdout)
    assert plan.expected_tasks == 8
    assert all(j.task_ids == [0, 1, 2, 3] for j in plan.jobs)
    assert plan.config.task_ids == {"mimic_iv_star": {"incre": [0, 1, 2, 3]}}


def test_ast_discovery_never_executes_checkout(experiment: Path) -> None:
    # Given
    runner = experiment.parent / "checkout" / "run.py"
    _ = runner.write_text(
        "raise RuntimeError('must never execute during dry-run')\n" + runner.read_text()
    )
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode == 0, result.stderr
    assert not (experiment.parent / "output").exists()


def test_explicit_unsupported_false_setting_is_rejected(experiment: Path) -> None:
    # Given
    runner = experiment.parent / "checkout" / "run.py"
    _ = runner.write_text(
        runner.read_text().replace(
            "p.add_argument('--verbose', action='store_true')", ""
        )
    )
    _ = experiment.write_text(
        experiment.read_text().replace(
            "run_timeout = 2", "run_timeout = 2\nverbose = false"
        )
    )
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode != 0
    assert "verbose" in result.stderr


def test_missing_coverage_is_rechecked_on_resume(experiment: Path) -> None:
    # Given
    first = launch(experiment, mode="missing")
    assert first.returncode == 1
    # When
    result = launch(experiment, "--resume")
    # Then
    assert result.returncode == 0, result.stderr
    summary = Summary.model_validate_json(result.stdout)
    assert summary.completed_tasks == 4
    assert all(not j.resumed for j in summary.jobs)


def test_resume_uses_filename_timestamp_and_ignores_usage_logs(
    experiment: Path,
) -> None:
    # Given
    first = launch(experiment)
    assert first.returncode == 0, first.stderr
    root = Path(Summary.model_validate_json(first.stdout).result_dir)
    for checkpoint in root.rglob("*.jsonl"):
        newer = checkpoint.with_name(
            checkpoint.name.replace("20260101000000", "20260102000000000000")
        )
        _ = newer.write_text(checkpoint.read_text())
        _ = checkpoint.write_text("")  # Older timestamp now has the newest mtime.
        _ = (checkpoint.parent / "usage.jsonl").write_text('{"tokens": 123}\n')
        _ = (checkpoint.parent / "usage_99999999999999.jsonl").write_text(
            '{"tokens": 123}\n'
        )
    # When
    result = launch(experiment, "--resume", mode="nonzero")
    # Then
    assert result.returncode == 0, result.stderr
    assert all(j.resumed for j in Summary.model_validate_json(result.stdout).jobs)


@pytest.mark.parametrize(
    "guidance, expected_code", [("benchmark", 2), ("identifier_free", 0), ("hidden", 0)]
)
def test_schema_removed_requires_schema_free_guidance(
    experiment: Path, guidance: str, expected_code: int
) -> None:
    # Given
    _ = experiment.write_text(
        experiment.read_text().replace(
            'tool_mode = "full"',
            f'tool_mode = "schema_removed"\nschema_guidance = "{guidance}"',
        )
    )
    # When
    result = launch(experiment, "--dry-run")
    # Then
    assert result.returncode == expected_code, result.stderr


@pytest.fixture
def ambiguous_cell_names(experiment: Path) -> Path:
    text = (
        experiment.read_text()
        .replace("mimic_iv_star", "mimic_iv")
        .replace("trials = 2", "trials = 1")
        .replace('name = "agent"', 'name = "x"')
        .replace('name = "full"', 'name = "a-mimic_iv-incre-b"')
    )
    _ = experiment.write_text(
        text
        + """
[[models]]
name = "x-mimic_iv-incre-a"
model = "openrouter/test/other"
temperature = 0.0

[[conditions]]
name = "b"
tool_mode = "full"
"""
    )
    return experiment


def test_structured_cell_identity_keeps_ambiguous_names_isolated(
    ambiguous_cell_names: Path,
) -> None:
    # Given: two different cells have identical delimiter-concatenated names.
    # When
    result = launch(ambiguous_cell_names, "--dry-run")
    # Then
    assert result.returncode == 0, result.stderr
    plan = Plan.model_validate_json(result.stdout)
    assert len(plan.jobs) == 4
    assert len({job.id for job in plan.jobs}) == 4
    assert len({job.checkpoint_dir for job in plan.jobs}) == 4
    assert len({job.log_path for job in plan.jobs}) == 4
    assert not Path(plan.result_dir).exists()
    repeated = Plan.model_validate_json(
        launch(ambiguous_cell_names, "--dry-run").stdout
    )
    assert [job.id for job in repeated.jobs] == [job.id for job in plan.jobs]


def test_resume_cannot_use_a_different_ambiguous_cell_checkpoint(
    ambiguous_cell_names: Path,
) -> None:
    # Given: four completed cells; remove only the first cell's checkpoint.
    first = launch(ambiguous_cell_names)
    assert first.returncode == 0, first.stderr
    root = Path(Summary.model_validate_json(first.stdout).result_dir)
    plan = Plan.model_validate_json((root / "manifest.json").read_bytes())
    target = next(
        job
        for job in plan.jobs
        if job.model == "x" and job.condition == "a-mimic_iv-incre-b"
    )
    for checkpoint in Path(target.checkpoint_dir).glob("*.jsonl"):
        checkpoint.unlink()
    # When: the rerun deliberately produces incomplete coverage.
    result = launch(ambiguous_cell_names, "--resume", mode="missing")
    # Then: only that cell reruns; another cell cannot satisfy its coverage.
    assert result.returncode == 1, result.stderr
    summary = Summary.model_validate_json(result.stdout)
    assert [job.id for job in summary.jobs if not job.resumed] == [target.id]
    assert not next(job for job in summary.jobs if job.id == target.id).complete
    assert len(list((root / "jobs").glob("*.json"))) == 4
    assert len(list((root / "logs").glob("*.log"))) == 4
    assert len(list((root / "checkpoints").iterdir())) == 4
