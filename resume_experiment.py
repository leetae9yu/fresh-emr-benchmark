#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.11,<3", "typing-extensions>=4.12"]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Preview a continuation without writing:
#      uv run resume_experiment.py --source-checkpoint results/subset.jsonl \
#        --dry-run -- .venv/bin/python run.py <FULL-RUN-ARGS>
# 3. Prepare and launch the unchanged runner:
#      uv run resume_experiment.py --source-checkpoint results/subset.jsonl \
#        -- .venv/bin/python run.py <FULL-RUN-ARGS>
# ──────────────────
# allow: SIZE_OK — user required one standalone, self-testing continuation file.

from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar, Final, final

from pydantic import BaseModel, ConfigDict, ValidationError
from typing_extensions import override

SCOPE_PATTERN: Final = re.compile(
    r"^(?P<head>.+)_k=(?P<trials>\d+)_range_.+?_user-(?P<tail>.+)$",
)
NAME_PROBE: Final = """
import sys
from run import parse_arguments
from src.utils import get_ckpt_name
sys.argv = ["run.py", *sys.argv[1:]]
print(get_ckpt_name(parse_arguments(), add_time=False))
"""


@dataclass(frozen=True, slots=True)
class ResumeError(Exception):
    detail: str

    def __post_init__(self) -> None:
        Exception.__init__(self, self.detail)


@dataclass(frozen=True, slots=True)
class CheckpointLine:
    sample_id: str
    payload: str


@dataclass(frozen=True, slots=True)
class CheckpointIdentity:
    signature: str
    trials: int


@dataclass(frozen=True, slots=True)
class CliConfig:
    source: Path
    dry_run: bool
    prepare_only: bool
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResumePlan:
    source: Path
    source_hash: str
    existing_target: Path | None
    seed: Path
    records: tuple[CheckpointLine, ...]
    command: tuple[str, ...]


class StoredRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="allow",
        frozen=True,
    )

    sample_id: str


@final
class ParsedArguments(argparse.Namespace):
    """Mutable boundary object populated by argparse."""

    @override
    def __init__(self) -> None:
        super().__init__()
        self.source_checkpoint: Path = Path()
        self.dry_run: bool = False
        self.prepare_only: bool = False
        self.command: list[str] = []


def checkpoint_identity(name: str) -> CheckpointIdentity:
    stem = name.removesuffix(".jsonl")
    prefix, separator, possible_timestamp = stem.rpartition("_")
    if separator and possible_timestamp.isdigit():
        stem = prefix
    match = SCOPE_PATTERN.fullmatch(stem)
    if match is None:
        raise ResumeError(f"unsupported checkpoint name: {name}")
    return CheckpointIdentity(
        signature=f"{match['head']}_user-{match['tail']}",
        trials=int(match["trials"]),
    )


def parse_checkpoint_line(raw_line: str, path: Path, number: int) -> CheckpointLine:
    try:
        record = StoredRecord.model_validate_json(raw_line)
    except ValidationError as error:
        raise ResumeError(f"{path}:{number}: {error}") from error
    return CheckpointLine(
        sample_id=record.sample_id,
        payload=raw_line.strip(),
    )


def read_checkpoint(path: Path) -> tuple[CheckpointLine, ...]:
    records: dict[str, CheckpointLine] = {}
    with path.open(encoding="utf-8") as checkpoint:
        for number, line in enumerate(checkpoint, start=1):
            if line.strip():
                record = parse_checkpoint_line(line, path, number)
                records[record.sample_id] = record
    return tuple(records.values())


def merge_checkpoint_records(
    subset: Sequence[CheckpointLine],
    existing: Sequence[CheckpointLine],
) -> tuple[CheckpointLine, ...]:
    merged: dict[str, CheckpointLine] = {}
    for record in (*subset, *existing):
        previous = merged.get(record.sample_id)
        if previous is not None and previous.payload != record.payload:
            raise ResumeError(f"conflicting sample_id: {record.sample_id}")
        merged[record.sample_id] = record
    return tuple(merged.values())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def option_value(command: Sequence[str], option: str, default: str) -> str:
    try:
        position = command.index(option)
    except ValueError:
        return default
    if position + 1 >= len(command):
        raise ResumeError(f"{option} requires a value")
    return command[position + 1]


def target_prefix(project_root: Path, command: Sequence[str]) -> str:
    if len(command) < 2 or Path(command[1]).name != "run.py":
        raise ResumeError("command must start with a Python interpreter and run.py")
    probe = subprocess.run(
        [command[0], "-c", NAME_PROBE, *command[2:]],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = probe.stdout.strip().splitlines()
    if not lines:
        raise ResumeError("run.py checkpoint-name probe returned no output")
    return lines[-1]


def latest_matching_checkpoint(result_dir: Path, prefix: str) -> Path | None:
    if not result_dir.exists():
        return None
    candidates = [
        path
        for path in result_dir.glob("*.jsonl")
        if path.stem.rpartition("_")[0] == prefix
        and path.stem.rpartition("_")[2].isdigit()
    ]
    return max(
        candidates,
        key=lambda path: path.stem.rpartition("_")[2],
        default=None,
    )


def next_seed_path(result_dir: Path, prefix: str) -> Path:
    timestamp = datetime.now(UTC)
    candidate = result_dir / f"{prefix}_{timestamp:%Y%m%d%H%M%S%f}.jsonl"
    while candidate.exists():
        timestamp += timedelta(microseconds=1)
        candidate = result_dir / f"{prefix}_{timestamp:%Y%m%d%H%M%S%f}.jsonl"
    return candidate


def build_plan(project_root: Path, config: CliConfig) -> ResumePlan:
    source = config.source.resolve(strict=True)
    prefix = target_prefix(project_root, config.command)
    source_identity = checkpoint_identity(source.name)
    target_identity = checkpoint_identity(prefix)
    if source_identity.signature != target_identity.signature:
        raise ResumeError("source and target experiment signatures differ")
    if source_identity.trials > target_identity.trials:
        raise ResumeError("target trial count is lower than source trial count")

    result_dir_value = option_value(config.command, "--result_dir", "results")
    result_dir = Path(result_dir_value)
    if not result_dir.is_absolute():
        result_dir = project_root / result_dir
    existing_target = latest_matching_checkpoint(result_dir, prefix)
    existing_records = (
        read_checkpoint(existing_target) if existing_target is not None else ()
    )
    records = merge_checkpoint_records(
        read_checkpoint(source),
        existing_records,
    )
    return ResumePlan(
        source=source,
        source_hash=sha256_file(source),
        existing_target=existing_target,
        seed=next_seed_path(result_dir, prefix),
        records=records,
        command=config.command,
    )


def write_seed(plan: ResumePlan) -> None:
    plan.seed.parent.mkdir(parents=True, exist_ok=True)
    with plan.seed.open("x", encoding="utf-8") as seed:
        for record in plan.records:
            _ = seed.write(record.payload + "\n")


def print_plan(plan: ResumePlan) -> None:
    print(f"source={plan.source}")
    print(f"source_sha256={plan.source_hash}")
    print(f"existing_target={plan.existing_target or 'none'}")
    print(f"seed={plan.seed}")
    print(f"seed_records={len(plan.records)}")
    print(f"command={shlex.join(plan.command)}")


def parse_cli(argv: Sequence[str]) -> CliConfig:
    parser = argparse.ArgumentParser(
        description="Resume a larger EHR-ChatQA run from an immutable checkpoint.",
    )
    _ = parser.add_argument("--source-checkpoint", type=Path, required=True)
    _ = parser.add_argument("--dry-run", action="store_true")
    _ = parser.add_argument("--prepare-only", action="store_true")
    _ = parser.add_argument("command", nargs=argparse.REMAINDER)
    namespace = ParsedArguments()
    _ = parser.parse_args(argv, namespace=namespace)
    command = tuple(namespace.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ResumeError("runner command is required after --")
    return CliConfig(
        source=namespace.source_checkpoint,
        dry_run=namespace.dry_run,
        prepare_only=namespace.prepare_only,
        command=command,
    )


def _run_self_tests() -> None:
    subset = (CheckpointLine("subset", '{"sample_id":"subset"}'),)
    existing = (CheckpointLine("full", '{"sample_id":"full"}'),)
    merged = merge_checkpoint_records(subset, existing)
    assert [record.sample_id for record in merged] == ["subset", "full"]

    left_name = (
        "env-incre-agent-model-0.0_k=1_range_1-2_"
        + "user-strategy-model-1.0_20260826000000.jsonl"
    )
    right_name = "env-incre-agent-model-0.0_k=5_range_0--1_" + "user-strategy-model-1.0"
    left = checkpoint_identity(left_name)
    right = checkpoint_identity(right_name)
    assert left.signature == right.signature
    assert (left.trials, right.trials) == (1, 5)

    with TemporaryDirectory() as directory:
        source = Path(directory) / "source.jsonl"
        _ = source.write_text('{"sample_id":"subset"}\n', encoding="utf-8")
        before = sha256_file(source)
        seed = Path(directory) / "seed.jsonl"
        plan = ResumePlan(
            source=source,
            source_hash=before,
            existing_target=None,
            seed=seed,
            records=subset,
            command=("python", "run.py"),
        )
        write_seed(plan)
        assert seed.read_text(encoding="utf-8") == '{"sample_id":"subset"}\n'
        assert sha256_file(source) == before
    print("self_tests=passed")


def run(config: CliConfig) -> int:
    project_root = Path(__file__).resolve().parent
    plan = build_plan(project_root, config)
    print_plan(plan)
    if config.dry_run:
        return 0
    write_seed(plan)
    if config.prepare_only:
        return 0
    completed = subprocess.run(plan.command, cwd=project_root, check=False)
    if sha256_file(plan.source) != plan.source_hash:
        raise ResumeError("source checkpoint changed during continuation")
    return completed.returncode


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        _run_self_tests()
        return 0
    try:
        return run(parse_cli(sys.argv[1:]))
    except (ResumeError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
