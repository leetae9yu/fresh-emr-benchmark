#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.8,<3"]
# ///
# How to run: uv run experiment_runner.py experiments/motivation.toml --dry-run
# Or: .venv/bin/python experiment_runner.py experiments/motivation.toml [--resume]
# SIZE_OK: the requested deliverable is one self-contained production file.
"""Plan and supervise run.py subprocesses; never import the benchmark engine.

Paths in TOML are relative to that TOML, except source.python (relative to the
source checkout). Credentials belong in the inherited environment, never TOML.
Dry-run only reads files and Git metadata. It does not execute source Python.
Each job is one trial; older engines use the manifest/directory trial identity.
On POSIX, process groups are killed at timeout, cancellation and normal exit;
Linux additionally adopts and reaps descendants to avoid orphan zombies.
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import fcntl
import hashlib
import itertools
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import tomllib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import FrameType
from typing import Annotated, ClassVar, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

Environment = Literal["mimic_iv", "mimic_iv_star", "eicu", "eicu_star"]
Flow = Literal["incre", "adapt"]
PositiveInt = Annotated[int, Field(gt=0)]
TaskId = Annotated[int, Field(ge=0)]
Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,47}$")]
ModelId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:@+-]*$")]
Reasoning = Literal["none", "minimal", "low", "medium", "high", "xhigh", "default"]


class ConfigModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False
    )


class Source(ConfigModel):
    path: str
    python: str = ".venv/bin/python"


class Defaults(ConfigModel):
    embedding_model: ModelId = "text-embedding-3-large"
    api_base: str | None = None
    agent_strategy: Literal["tool-calling"] = "tool-calling"
    max_concurrency: PositiveInt = 1
    max_agent_turns: PositiveInt = 30
    max_retry: PositiveInt = 10
    timeout: PositiveInt = 600
    run_timeout: Annotated[float, Field(gt=0)] = 3600.0
    reward_scope: Literal["any", "final"] = "any"
    reasoning_effort: Reasoning | None = None
    max_completion_tokens: PositiveInt | None = None
    verbose: bool = False

    @field_validator("api_base")
    @classmethod
    def credential_free_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "api_base must be an HTTP(S) URL without credentials, query or fragment"
                )
        return value


class AgentModel(ConfigModel):
    name: Name
    model: ModelId
    temperature: Annotated[float, Field(ge=0, le=2)]
    reasoning_effort: Reasoning | None = None
    max_completion_tokens: PositiveInt | None = None


class UserModel(ConfigModel):
    model: ModelId
    temperature: Annotated[float, Field(ge=0, le=2)]
    strategy: Literal["nested-reflection"]


class ValidatorModel(ConfigModel):
    model: ModelId
    trials: PositiveInt


class Condition(ConfigModel):
    name: Name
    tool_mode: Literal["full", "schema_removed", "sql_only", "sql_value"]
    metadata_access: Literal["allowed", "blocked"] = "allowed"
    failure_feedback: Literal["detailed", "binary"] = "detailed"
    schema_guidance: Literal["benchmark", "identifier_free", "hidden"] = "benchmark"

    @model_validator(mode="after")
    def guidance_default(self) -> Self:
        if (
            self.tool_mode == "schema_removed"
            and "schema_guidance" not in self.model_fields_set
        ):
            return self.model_copy(update={"schema_guidance": "identifier_free"})
        if self.tool_mode == "schema_removed" and self.schema_guidance == "benchmark":
            raise ValueError("schema_removed requires identifier_free or hidden schema_guidance")
        return self


class LaunchConfig(ConfigModel):
    name: Name
    description: str = ""
    source: Source
    result_root: str = "results/config-runner"
    parallel_cells: PositiveInt = 1
    trials: PositiveInt = 1
    envs: Annotated[list[Environment], Field(min_length=1)]
    task_types: Annotated[list[Flow], Field(min_length=1)]
    models: Annotated[list[AgentModel], Field(min_length=1)]
    conditions: Annotated[list[Condition], Field(min_length=1)]
    defaults: Defaults
    user: UserModel
    validator: ValidatorModel
    task_ids: dict[
        Environment, dict[Flow, Annotated[list[TaskId], Field(min_length=1)]]
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def grid_is_unambiguous(self) -> Self:
        axes = [
            self.envs,
            self.task_types,
            [m.name for m in self.models],
            [c.name for c in self.conditions],
        ]
        if any(len(axis) != len(set(axis)) for axis in axes):
            raise ValueError("grid axes and model/condition names must be unique")
        if self.task_ids and set(self.task_ids) != set(self.envs):
            raise ValueError("task_ids must specify exactly the selected environments")
        for flows in self.task_ids.values():
            if set(flows) != set(self.task_types):
                raise ValueError(
                    "task_ids must specify exactly the selected task_types for each environment"
                )
            if any(len(ids) != len(set(ids)) for ids in flows.values()):
                raise ValueError(
                    "task_ids must be unique within each environment/task_type"
                )
        return self


class SourceIdentity(ConfigModel):
    path: str
    python: str
    git_commit: str | None
    dirty: bool | None
    code_digest: str
    launcher_digest: str


class Job(ConfigModel):
    id: str
    model: str
    env: Environment
    task_type: Flow
    condition: str
    schema_guidance: str
    trial_id: PositiveInt
    task_ids: list[TaskId]
    native_trial_id: bool
    checkpoint_dir: str
    log_path: str
    command: list[str]


class Plan(ConfigModel):
    format_version: int = 1
    config_hash: str
    config: LaunchConfig
    source: SourceIdentity
    result_dir: str
    expected_tasks: int
    jobs: list[Job]


class TaskRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", strict=True)
    task_id: str
    db_id: str
    task_type: str


class CheckpointRecord(TaskRecord):
    trial_id: int | None = None
    sample_id: str
    reward: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None


class Coverage(ConfigModel):
    expected: int
    completed: int
    missing_task_ids: list[int]
    duplicate_task_ids: list[int] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    complete: bool


class JobStatus(ConfigModel):
    id: str
    returncode: int | None
    timed_out: bool = False
    cancelled: bool = False
    resumed: bool = False
    coverage: Coverage
    complete: bool


class Summary(ConfigModel):
    config_hash: str
    result_dir: str
    expected_tasks: int
    completed_tasks: int
    complete: bool
    jobs: list[JobStatus]


def load_config(path: Path) -> LaunchConfig:
    with path.open("rb") as stream:
        config = LaunchConfig.model_validate(tomllib.load(stream))
    source = (path.parent / config.source.path).resolve()
    # Do not resolve a venv interpreter symlink: that would bypass the venv.
    requested_python = config.source.python
    python = shutil.which(requested_python) if "/" not in requested_python else None
    python = python or os.path.abspath(source / requested_python)
    if not (source / "run.py").is_file():
        raise ValueError(f"source has no run.py: {source}")
    if not os.path.isfile(python) or not os.access(python, os.X_OK):
        raise ValueError("source.python must identify an executable Python interpreter")
    return config.model_copy(
        update={
            "source": Source(path=str(source), python=python),
            "result_root": str((path.parent / config.result_root).resolve()),
        }
    )


def source_identity(source: Source) -> SourceIdentity:
    root = Path(source.path)
    # Hash runtime code, prompts, schemas, task catalogs and dependency metadata,
    # including dirty/untracked code, but never secrets, DBs, caches or results.
    paths = set(root.glob("*.py")) | {
        root / "requirements.txt",
        root / "pyproject.toml",
        root / "uv.lock",
    }
    for folder in (root / "src", root / "scripts"):
        if folder.exists():
            paths.update(
                p
                for p in folder.rglob("*")
                if p.suffix
                in {".py", ".txt", ".json", ".jsonl", ".sql", ".sh", ".toml"}
            )
    digest = hashlib.sha256()
    code_paths = sorted(p for p in paths if p.is_file())
    for path in code_paths:
        digest.update(str(path.relative_to(root)).encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    git = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = git.stdout.strip() if git.returncode == 0 else None
    dirty = None
    if commit is not None:
        status = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *[str(p.relative_to(root)) for p in code_paths],
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        dirty = bool(status.stdout.strip())
    return SourceIdentity(
        path=source.path,
        python=source.python,
        git_commit=commit,
        dirty=dirty,
        code_digest=digest.hexdigest(),
        launcher_digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )


def cli_options(source: Path) -> dict[str, set[str] | None]:
    """Read argparse declarations and literal/enum choices without executing code."""
    enums: dict[str, set[str]] = {}
    enum_file = source / "src" / "experiment.py"
    if enum_file.is_file():
        for node in ast.walk(ast.parse(enum_file.read_text())):
            if isinstance(node, ast.ClassDef):
                enums[node.name] = {
                    n.value.value
                    for n in node.body
                    if isinstance(n, ast.Assign)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)
                }
    options: dict[str, set[str] | None] = {}
    for node in ast.walk(ast.parse((source / "run.py").read_text())):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        choices: set[str] | None = None
        for keyword in node.keywords:
            if keyword.arg == "choices":
                value = keyword.value
                if isinstance(value, (ast.List, ast.Tuple)) and all(
                    isinstance(v, ast.Constant) for v in value.elts
                ):
                    choices = {
                        str(v.value) for v in value.elts if isinstance(v, ast.Constant)
                    }
                elif (
                    isinstance(value, ast.ListComp)
                    and len(value.generators) == 1
                    and isinstance(value.generators[0].iter, ast.Name)
                ):
                    choices = enums.get(value.generators[0].iter.id)
                if choices is None:
                    raise ValueError(
                        "cannot statically determine argparse choices; use a checkout with literal or enum CLI choices"
                    )
        for arg in node.args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value.startswith("--")
            ):
                options[arg.value] = choices
    return options


def build_plan(config: LaunchConfig) -> Plan:
    source = Path(config.source.path)
    identity = source_identity(config.source)
    options = cli_options(source)
    selections: dict[Environment, dict[Flow, list[int]]] = {}
    for env, flow in itertools.product(config.envs, config.task_types):
        # Original schemas derive the same task list from the star annotations.
        catalog_env = env if env.endswith("_star") else env + "_star"
        catalog = source / "src" / "envs" / catalog_env / f"eval_{flow}.jsonl"
        records = TypeAdapter(list[TaskRecord]).validate_json(catalog.read_bytes())
        selected = (
            config.task_ids[env][flow] if config.task_ids else list(range(len(records)))
        )
        if not selected:
            raise ValueError(f"empty task catalog for {env}/{flow}")
        selections.setdefault(env, {})[flow] = selected
        for task_id in selected:
            if task_id >= len(records) or records[task_id].task_id != str(task_id):
                raise ValueError(
                    f"task_id {task_id} is not a valid runtime index for {env}/{flow}"
                )
            if (
                records[task_id].db_id != catalog_env
                or records[task_id].task_type != flow
            ):
                raise ValueError(f"task catalog identity mismatch for {env}/{flow}")
    config = config.model_copy(update={"task_ids": selections})
    payload = {
        "config": config.model_dump(mode="json"),
        "source": identity.model_dump(mode="json"),
        "format_version": 1,
    }
    config_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result_dir = Path(config.result_root) / f"{config.name}-{config_hash}"
    jobs: list[Job] = []
    for model, env, flow, condition, trial in itertools.product(
        config.models,
        config.envs,
        config.task_types,
        config.conditions,
        range(1, config.trials + 1),
    ):
        cell_identity = json.dumps(
            (model.name, env, flow, condition.name, trial), separators=(",", ":")
        )
        cell_digest = hashlib.sha256(cell_identity.encode()).hexdigest()
        job_id = f"{model.name}-{env}-{flow}-{condition.name}-trial-{trial}-{cell_digest}"
        checkpoint_dir = result_dir / "checkpoints" / job_id
        values: dict[str, str | int | float | bool | list[int] | None] = (
            config.defaults.model_dump(exclude={"run_timeout"})
        )
        values.update(
            model.model_dump(
                exclude={"name", "reasoning_effort", "max_completion_tokens"}
            )
        )
        for key in ("reasoning_effort", "max_completion_tokens"):
            if key in model.model_fields_set:
                values[key] = getattr(model, key)
        values.update(condition.model_dump(exclude={"name"}))
        values.update(
            env=env,
            task_type=flow,
            user_model=config.user.model,
            user_temperature=config.user.temperature,
            user_strategy=config.user.strategy,
            validation_model=config.validator.model,
            validation_trials=config.validator.trials,
            num_trials=1,
            result_dir=str(checkpoint_dir),
            task_ids=config.task_ids[env][flow],
        )
        native_trial_id = "--trial_id" in options
        if native_trial_id:
            values["trial_id"] = trial
        if (
            "--reward_scope" not in options
            and "reward_scope" not in config.defaults.model_fields_set
        ):
            del values[
                "reward_scope"
            ]  # Historical engines have implicit reward_scope=any.
        command = [config.source.python, "-B", str(source / "run.py")]
        for name, value in values.items():
            if value is None:
                continue
            flag = "--" + name
            if flag not in options:
                raise ValueError(f"source run.py does not support requested {flag}")
            if value is False:
                continue
            arguments = (
                []
                if value is True
                else [str(v) for v in value]
                if isinstance(value, list)
                else [str(value)]
            )
            choices = options[flag]
            if choices is not None and any(arg not in choices for arg in arguments):
                raise ValueError(
                    f"source run.py does not support requested value for {flag}"
                )
            command.extend([flag, *arguments])
        jobs.append(
            Job(
                id=job_id,
                model=model.name,
                env=env,
                task_type=flow,
                condition=condition.name,
                schema_guidance=condition.schema_guidance,
                trial_id=trial,
                task_ids=config.task_ids[env][flow],
                native_trial_id=native_trial_id,
                checkpoint_dir=str(checkpoint_dir),
                log_path=str(result_dir / "logs" / f"{job_id}.log"),
                command=command,
            )
        )
    if len({job.id for job in jobs}) != len(jobs):
        raise ValueError("generated job identities must be unique")
    return Plan(
        config_hash=config_hash,
        config=config,
        source=identity,
        result_dir=str(result_dir),
        expected_tasks=sum(len(job.task_ids) for job in jobs),
        jobs=jobs,
    )


def checkpoint_coverage(job: Job) -> Coverage:
    expected = set(job.task_ids)
    files: list[tuple[str, Path]] = []
    for path in Path(job.checkpoint_dir).glob("*.jsonl"):
        # Jobs own isolated checkpoint directories. Recognize benchmark names,
        # not usage/log JSONL, and order timestamp strings exactly like run.py.
        if (
            path.name.startswith(f"{job.env}-{job.task_type}-")
            and "_k=1_range_" in path.name
            and "_user-" in path.name
        ):
            timestamp = re.search(r"_(\d{14}|\d{20})\.jsonl$", path.name)
            files.append((timestamp.group(1) if timestamp else "", path))
    records: dict[str, CheckpointRecord] = {}
    errors: list[str] = []
    if files:
        # run.py writes cumulative snapshots. Combining snapshots double-counts.
        latest = max(files, key=lambda item: (item[0], item[1].name))[1]
        for line_number, line in enumerate(latest.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = CheckpointRecord.model_validate_json(line)
            except ValidationError:
                errors.append(f"invalid checkpoint record at line {line_number}")
                continue
            if (
                record.db_id != job.env
                or record.task_type != job.task_type
                or (record.trial_id is not None and record.trial_id != job.trial_id)
                or (job.native_trial_id and record.trial_id is None)
                or record.task_id not in {str(i) for i in expected}
            ):
                errors.append(f"unexpected checkpoint identity at line {line_number}")
                continue
            records[record.sample_id] = record
    counts = Counter(int(r.task_id) for r in records.values() if r.reward is not None)
    missing = sorted(expected - counts.keys())
    duplicates = sorted(task for task, count in counts.items() if count != 1)
    return Coverage(
        expected=len(expected),
        completed=len(counts),
        missing_task_ids=missing,
        duplicate_task_ids=duplicates,
        errors=errors,
        complete=not (missing or duplicates or errors),
    )


def save_json(path: Path, value: BaseModel) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    _ = temporary.write_text(value.model_dump_json(indent=2) + "\n")
    _ = temporary.replace(path)


def kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return  # The process group has already exited; cleanup is complete.


class Supervisor:
    """Mutable registry synchronizes subprocess startup with signal cancellation."""

    def __init__(self, plan: Plan, resume: bool) -> None:
        self.plan: Plan = plan
        self.resume: bool = resume
        self.cancelled: threading.Event = threading.Event()
        self.lock: threading.Lock = threading.Lock()
        self.active: set[int] = set()

    def cancel(self, _signum: int, _frame: FrameType | None) -> None:
        self.cancelled.set()
        with self.lock:
            for pid in self.active:
                kill_group(pid)

    def run_job(self, job: Job) -> JobStatus:
        coverage = checkpoint_coverage(job)
        if self.resume and coverage.complete:
            return JobStatus(
                id=job.id,
                returncode=None,
                resumed=True,
                coverage=coverage,
                complete=True,
            )
        timed_out = False
        returncode = None
        if not self.cancelled.is_set():
            Path(job.checkpoint_dir).mkdir(parents=True, exist_ok=True)
            with Path(job.log_path).open("a") as log:
                with self.lock:
                    if self.cancelled.is_set():
                        process = None
                    else:
                        process = subprocess.Popen(
                            job.command,
                            cwd=self.plan.source.path,
                            stdin=subprocess.DEVNULL,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            start_new_session=True,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        )
                        self.active.add(process.pid)
                if process is not None:
                    try:
                        returncode = process.wait(
                            timeout=self.plan.config.defaults.run_timeout
                        )
                    except subprocess.TimeoutExpired:
                        timed_out = True
                    finally:
                        with self.lock:
                            kill_group(process.pid)
                            self.active.remove(process.pid)
                        returncode = process.wait()
                        if sys.platform == "linux":
                            # Adopted grandchildren are scoped by this job's PGID.
                            while True:
                                try:
                                    _ = os.waitpid(-process.pid, 0)
                                except ChildProcessError:
                                    break
            coverage = checkpoint_coverage(job)
        status = JobStatus(
            id=job.id,
            returncode=returncode,
            timed_out=timed_out,
            cancelled=self.cancelled.is_set(),
            coverage=coverage,
            complete=returncode == 0
            and not timed_out
            and not self.cancelled.is_set()
            and coverage.complete,
        )
        save_json(Path(self.plan.result_dir) / "status" / f"{job.id}.json", status)
        return status


def execute(plan: Plan, resume: bool) -> Summary:
    root = Path(plan.result_dir)
    if root.exists() and not resume:
        raise ValueError(
            "result directory already exists; use --resume for the identical config"
        )
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another launcher owns this result directory") from exc
        manifest = root / "manifest.json"
        if manifest.exists():
            previous = Plan.model_validate_json(manifest.read_bytes())
            if previous.model_dump() != plan.model_dump():
                raise ValueError(
                    "existing manifest does not match the resolved config and code"
                )
        else:
            if any(p.name != ".lock" for p in root.iterdir()):
                raise ValueError(
                    "refusing to reuse results without a matching manifest"
                )
            save_json(manifest, plan)
        for directory in ("logs", "jobs", "status", "checkpoints"):
            (root / directory).mkdir(exist_ok=True)
        for job in plan.jobs:
            save_json(root / "jobs" / f"{job.id}.json", job)
        if sys.platform == "linux":
            # PR_SET_CHILD_SUBREAPER: timeout cleanup also reaps orphan descendants.
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(36, 1, 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), "cannot enable child subreaper")
        supervisor = Supervisor(plan, resume)
        previous_signals = {
            sig: signal.signal(sig, supervisor.cancel)
            for sig in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            with ThreadPoolExecutor(
                max_workers=min(plan.config.parallel_cells, len(plan.jobs))
            ) as executor:
                statuses = list(executor.map(supervisor.run_job, plan.jobs))
        finally:
            for sig, handler in previous_signals.items():
                _ = signal.signal(sig, handler)
        summary = Summary(
            config_hash=plan.config_hash,
            result_dir=plan.result_dir,
            expected_tasks=plan.expected_tasks,
            completed_tasks=sum(s.coverage.completed for s in statuses),
            complete=all(s.complete for s in statuses),
            jobs=statuses,
        )
        save_json(root / "summary.json", summary)
        return summary


class Arguments(ConfigModel):
    config: Path
    dry_run: bool = False
    resume: bool = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("config", type=Path, help="TOML experiment configuration")
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved manifest; no writes or benchmark execution",
    )
    _ = parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse identical config/code and check expected task coverage",
    )
    args = Arguments.model_validate(vars(parser.parse_args(argv)))
    try:
        plan = build_plan(load_config(args.config.resolve()))
        if args.dry_run:
            print(plan.model_dump_json(indent=2))
            return 0
        summary = execute(plan, args.resume)
        print(summary.model_dump_json(indent=2))
        return 0 if summary.complete else 1
    except ValidationError as exc:
        # Never echo rejected input values (which may contain credentials).
        print(
            json.dumps(
                {
                    "error": "validation",
                    "details": exc.errors(include_input=False, include_context=False),
                }
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f"experiment_runner: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
