"""Small paired Original/Star Full-versus-ATD generation probe."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Final

from sqlglot import exp, parse_one

ROOT: Final = Path(__file__).resolve().parents[2]
LOGITS: Final = ROOT / "logits"
for entry in (str(ROOT), str(LOGITS)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from src.gt_conversion import DatabaseSchema, convert_gold_sql

from nl2sql_poc.core import CoreError, extract_sql
from paper2402_experiment.candidates import fingerprint_rows
from paper2402_experiment.ddl import disconnect
from paper2402_experiment.models import (
    BuildError,
    Database,
    Dataset,
    Fingerprint,
    Variant,
)
from paper2402_experiment.run import ATD_SYSTEM, execute, extract_identifier
from paper2402_experiment.sources import PATHS, catalog, sha256

HERE: Final = Path(__file__).resolve().parent
OUTPUT: Final = HERE / "quick_atd_poc"
SELECTION: Final[dict[Database, tuple[str, ...]]] = {
    "mimic_iv": ("6", "9", "10", "46"),
    "eicu": ("0", "8", "9", "42"),
}
EXISTING: Final = {
    "mimic_iv": {"0", "4", "12"},
    "eicu": {"1", "11"},
}
ANNOTATION_MISMATCH: Final = {("eicu", "42")}


def build() -> dict[str, list[dict[str, str | int]]]:
    """Freeze matched new tasks before any inference, checking both gold results."""
    jobs: list[dict[str, str | int]] = []
    for database, selected in SELECTION.items():
        if set(selected) & EXISTING[database]:
            raise BuildError("selection", database)
        tasks_path = ROOT / f"src/envs/{database}_star/eval_incre.jsonl"
        tasks = {task["task_id"]: task for task in json.loads(tasks_path.read_text())}
        catalogs = {
            variant: catalog(database, variant)
            for variant in ("original", "star")
        }
        for task_id in selected:
            task = tasks[task_id]
            sql_by_variant: dict[Variant, str] = {
                "star": task["gold_sql"],
                "original": convert_gold_sql(
                    task["gold_sql"], DatabaseSchema(database)
                ),
            }
            original, original_error = execute(
                database, "original", sql_by_variant["original"]
            )
            star, star_error = execute(database, "star", sql_by_variant["star"])
            if (
                original is None
                or star is None
                or original_error is not None
                or star_error is not None
            ):
                raise BuildError(
                    "gold execution",
                    f"{database}:{task_id}:{original_error}:{star_error}",
                )
            if original != star:
                raise BuildError("gold mismatch", f"{database}:{task_id}")
            outcomes: dict[Variant, Fingerprint] = {
                "original": original,
                "star": star,
            }
            expected = fingerprint_rows(
                sorted(
                    [[str(value) for value in row] for row in task["gold_answer"]]
                )[:100]
            )
            if star != expected:
                print(
                    f"ANNOTATED_ANSWER_MISMATCH {database}:{task_id} "
                    f"gold_sql={star.sha256} "
                    f"gold_answer={expected.sha256}",
                    file=sys.stderr,
                )
            for variant, sql in sql_by_variant.items():
                tree = parse_one(sql, read="sqlite")
                names = {table.name for table in tree.find_all(exp.Table)}
                ddls = [
                    ddl for name, ddl in catalogs[variant].items() if name in names
                ]
                if len(ddls) < 2:
                    raise BuildError("tables", f"{database}:{task_id}:{variant}")
                full = "\n\n".join(ddls)
                parts = [disconnect(ddl) for ddl in ddls]
                atd = "\n\n".join(ddl for ddl, _ in parts)
                removed = sum(count for _, count in parts)
                if removed < 1 or "FOREIGN KEY" in atd.upper():
                    raise BuildError("FK disconnection", f"{database}:{task_id}")
                for condition, ddl in (("full", full), ("atd", atd)):
                    jobs.append(
                        {
                            "job_id": f"{database}:{task_id}:{variant}:{condition}",
                            "database": database,
                            "task_id": task_id,
                            "variant": variant,
                            "condition": condition,
                            "removed_fks": removed,
                            "system": ATD_SYSTEM,
                            "prompt": (
                                "Write a read-only SQLite query that answers this "
                                f"request.\n\n{task['instruction']}\n\n"
                                f"Schema:\n{ddl}\n\nSQL:"
                            ),
                            "max_new_tokens": 256,
                            "gold_sha256": outcomes[variant].sha256,
                        }
                    )
    if len(jobs) != 32:
        raise BuildError("coverage", str(len(jobs)))
    return {
        "jobs": jobs,
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
            }
            for path in (
                ROOT / "src/envs/mimic_iv_star/eval_incre.jsonl",
                ROOT / "src/envs/eicu_star/eval_incre.jsonl",
                *(PATHS.values()),
            )
        ],
    }


def analyze() -> None:
    jobs_path = OUTPUT / "jobs.json"
    jobs = json.loads(jobs_path.read_text())
    for source in jobs["sources"]:
        if sha256(ROOT / source["path"]) != source["sha256"]:
            raise BuildError("source drift", source["path"])
    raw = (OUTPUT / "infer_qwen.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in raw]
    expected = {job["job_id"]: job for job in jobs["jobs"]}
    if len(rows) != len(expected) or {row["job_id"] for row in rows} != set(
        expected
    ):
        raise BuildError("output coverage", f"{len(rows)}/{len(expected)}")
    if (OUTPUT / "jobs_sha256.txt").read_text().strip() != hashlib.sha256(
        jobs_path.read_bytes()
    ).hexdigest():
        raise BuildError("job digest", "remote input differs")
    scored: list[dict[str, str | bool | None]] = []
    for row in rows:
        job = expected[row["job_id"]]
        sql: str | None = None
        error: str | None = None
        result = None
        try:
            sql = extract_sql(row["text"])
        except CoreError as failure:
            error = str(failure)
        else:
            result, error = execute(job["database"], job["variant"], sql)
        scored.append(
            {
                "job_id": row["job_id"],
                "sql": sql,
                "error": error,
                "executable": result is not None,
                "correct": result is not None
                and result.sha256 == job["gold_sha256"],
            }
        )
    summary: dict[str, dict[str, dict[str, int]]] = {}
    for cohort in ("primary", "all"):
        cells: dict[str, dict[str, int]] = {}
        for variant in ("original", "star"):
            for condition in ("full", "atd"):
                selected = [
                    row
                    for row in scored
                    if expected[row["job_id"]]["variant"] == variant
                    and expected[row["job_id"]]["condition"] == condition
                    and (
                        cohort == "all"
                        or (
                            expected[row["job_id"]]["database"],
                            expected[row["job_id"]]["task_id"],
                        )
                        not in ANNOTATION_MISMATCH
                    )
                ]
                cells[f"{variant}_{condition}"] = {
                    "correct": sum(row["correct"] is True for row in selected),
                    "executable": sum(row["executable"] is True for row in selected),
                    "total": len(selected),
                }
        summary[cohort] = cells
    (OUTPUT / "analysis.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "excluded_from_primary": ["eicu:42"],
                "rows": scored,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))


def analyze_dc() -> None:
    """Score fresh exact generation on the previously frozen paired masks."""
    source = HERE / "dataset.json"
    dataset = Dataset.model_validate_json(source.read_text())
    jobs_path = OUTPUT / "dc_jobs.json"
    frozen = json.loads(jobs_path.read_text())
    if frozen["source_sha256"] != sha256(source):
        raise BuildError("DC source drift", str(source))
    if (OUTPUT / "dc_jobs_sha256.txt").read_text().strip() != sha256(jobs_path):
        raise BuildError("DC job digest", str(jobs_path))
    rows = [
        json.loads(line) for line in (OUTPUT / "infer_dc.jsonl").read_text().splitlines()
    ]
    expected = {f"{item.item_id}|gen": item for item in dataset.dc_items}
    if len(rows) != len(expected) or {row["job_id"] for row in rows} != set(
        expected
    ):
        raise BuildError("DC output coverage", f"{len(rows)}/{len(expected)}")
    scored = []
    for row in rows:
        item = expected[row["job_id"]]
        prediction = extract_identifier(row["text"], item.mask_token)
        scored.append(
            {
                "job_id": row["job_id"],
                "database": item.database,
                "variant": item.variant,
                "cluster_id": item.cluster_id,
                "answer": item.answer,
                "prediction": prediction,
                "exact": prediction == item.answer.lower(),
            }
        )
    summary = {}
    for database in ("mimic_iv", "eicu", "all"):
        for variant in ("original", "star"):
            chosen = [
                row
                for row in scored
                if row["variant"] == variant
                and (database == "all" or row["database"] == database)
            ]
            summary[f"{database}_{variant}"] = {
                "exact": sum(row["exact"] is True for row in chosen),
                "total": len(chosen),
                "tables": len({row["cluster_id"] for row in chosen}),
            }
    (OUTPUT / "dc_analysis.json").write_text(
        json.dumps({"summary": summary, "rows": scored}, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


def main() -> None:
    match sys.argv[1:]:
        case ["prepare-dc"]:
            source = HERE / "dataset.json"
            frozen = json.loads((HERE / "jobs.json").read_text())
            jobs = [
                job for job in frozen["generate"] if job["job_id"].startswith("dc:")
            ]
            if len(jobs) != 78:
                raise BuildError("DC jobs", str(len(jobs)))
            path = OUTPUT / "dc_jobs.json"
            if path.exists():
                raise BuildError("immutable DC jobs", str(path))
            path.write_text(
                json.dumps(
                    {"source_sha256": sha256(source), "jobs": jobs}, indent=2
                )
                + "\n"
            )
            print("QUICK_DC_JOBS", len(jobs))
        case ["analyze-dc"]:
            analyze_dc()
        case ["check"]:
            saved = json.loads((OUTPUT / "jobs.json").read_text())
            if saved != build():
                raise BuildError("job drift", "frozen inputs changed")
            print("QUICK_ATD_INPUT_OK", len(saved["jobs"]))
        case ["prepare"]:
            OUTPUT.mkdir(exist_ok=True)
            path = OUTPUT / "jobs.json"
            if path.exists():
                raise BuildError("immutable jobs", str(path))
            path.write_text(json.dumps(build(), indent=2) + "\n")
            print("QUICK_ATD_JOBS", path)
        case ["analyze"]:
            analyze()
        case _:
            raise SystemExit(
                "quick_atd_poc.py prepare|check|analyze|prepare-dc|analyze-dc"
            )


if __name__ == "__main__":
    main()
