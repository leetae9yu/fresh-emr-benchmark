"""Regression tests for the recovered GPT-2 score artifact."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Final, Literal, TypedDict, cast

ROOT: Final = Path(__file__).resolve().parent
REVISION: Final = "15ea56dee5df4983c59b2538573817e1667135e2"
EXCLUDED: Final = {
    "iii_only.00.mimiciii_clinical",
    "iv_only.11.mimiciv_icu",
    "iv_only.12.mimiciv_hosp",
    "iii_only.09.icustay_id",
    "iv_only.23.stay_id",
    "iv_only.17.edstay",
}


class ScoreRow(TypedDict):
    item_id: str
    stratum: str
    answer: str
    candidate: str
    sum_logprob: float
    mean_logprob: float
    token_count: int


class ScoreArtifact(TypedDict):
    model_revision: str
    dataset_sha256: str
    rows: list[ScoreRow]


class Payload(TypedDict):
    version: ScoreArtifact
    dictionary: ScoreArtifact


def load_payload() -> Payload:
    text = (ROOT / "gpt2_remote_stdout.txt").read_text()
    match = re.fullmatch(r"GPT2_RESULT_B64=(\S+)\n?", text)
    assert match is not None
    return cast(
        "Payload",
        json.loads(gzip.decompress(base64.b64decode(match.group(1)))),
    )


def test_payload_provenance_and_finite_rows() -> None:
    payload = load_payload()
    expected: tuple[
        tuple[Literal["version", "dictionary"], int, Path],
        ...,
    ] = (
        (
            "version",
            255,
            ROOT / "pythia_iv_exposure/version_eval_dataset.json",
        ),
        (
            "dictionary",
            655,
            ROOT / "pythia_dictionary_logits/dataset.json",
        ),
    )
    for name, count, dataset in expected:
        artifact: ScoreArtifact = payload[name]
        assert artifact["model_revision"] == REVISION
        assert artifact["dataset_sha256"] == hashlib.sha256(
            dataset.read_bytes(),
        ).hexdigest()
        assert len(artifact["rows"]) == count
        assert all(
            row["token_count"] > 0
            and math.isfinite(row["sum_logprob"])
            and math.isfinite(row["mean_logprob"])
            for row in artifact["rows"]
        )


def item_margins(rows: list[ScoreRow]) -> dict[str, tuple[str, float]]:
    grouped: dict[str, list[ScoreRow]] = {}
    for row in rows:
        grouped.setdefault(row["item_id"], []).append(row)
    result: dict[str, tuple[str, float]] = {}
    for item_id, candidates in grouped.items():
        answer = next(
            row for row in candidates
            if row["candidate"] == row["answer"]
        )
        distractors = [
            row["mean_logprob"]
            for row in candidates
            if row["candidate"] != row["answer"]
        ]
        result[item_id] = (
            answer["stratum"],
            answer["mean_logprob"] - statistics.fmean(distractors),
        )
    return result


def version_gap(
    margins: dict[str, tuple[str, float]],
    excluded: set[str],
) -> float:
    iii = [
        margin for item_id, (stratum, margin) in margins.items()
        if item_id not in excluded and stratum == "iii_only"
    ]
    iv = [
        margin for item_id, (stratum, margin) in margins.items()
        if item_id not in excluded and stratum == "iv_only"
    ]
    return statistics.fmean(iii) - statistics.fmean(iv)


def test_version_contrasts_reproduce() -> None:
    margins = item_margins(load_payload()["version"]["rows"])
    assert math.isclose(
        version_gap(margins, set()),
        1.804557245501634,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        version_gap(margins, EXCLUDED),
        2.3897315107451544,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
