# Historical experiment corrections

**Date:** 2026-09-07
**Scope:** One confirmed SQL scoring error and eight failed-validator records
from the four-model stratified cost pilot. No new agent trajectories,
optional timeout reruns, replacement simulations, or experiment cells.

## Corrected status

The original cohort contains 96 selected outcomes. After the bounded repair,
88 remain valid and eight are quarantined by the replayed validator. One
previous success is a failure, leaving 28 successes among the retained records.

| Agent | Original successes / 24 | Retained valid | Invalid / quarantined | Corrected successes |
|---|---:|---:|---:|---:|
| Gemini 2.5 Flash-Lite | 2/24 | 22 | 2 | 2 |
| Gemini 2.5 Flash | 6/24 | 23 | 1 | 6 |
| Gemini 3.5 Flash | 15/24 | 23 | 1 | 15 |
| Gemini 2.5 Pro | 6/24 | 20 | 4 | 5 |

These are not four complete, equally sized 24-outcome cohorts. Invalid
simulations are not ordinary reward-0 agent failures. No replacements were
generated, in accordance with the requested scope. Valid-subset rates must
not be presented as directly comparable full-cohort benchmark rates.

## Confirmed local score correction

- Agent: Gemini 2.5 Pro.
- Condition: MIMIC Original, IncreQA task 20, SQL-only, metadata blocked,
  detailed feedback, identifier-free guidance.
- Sample: `86f3478a-e5e6-4d55-bbce-30fc7019c475`.
- Reward: **1 -> 0**.
- Historical winning replay: `PRAGMA table_info(diagnoses_icd)`.
- Actual tool call: `tool_sql_execute_GVS17ezyG3obmqsnfNcx`.
- Actual observation: `Error: (sqlite3.DatabaseError) not authorized`.

The old scorer replayed the denied PRAGMA without the metadata restriction.
Its NOT NULL column contained ones, which matched the gold scalar answer.
All 20 actual SQL calls were checked, including five successful full outputs;
none of those successful outputs matched the gold answer. The current
any-hit scorer reproduced reward 0 from those stored live results. No model
request was needed for this correction.

## Eight validator replays

Config: `experiments/historical-validator-repair.toml`.
Validator: `openrouter/google/gemini-2.5-flash`, one decision per stored
conversation, default validator temperature 0.0.

Each original record had nonempty messages but had been accepted with the
explanation `Validator failed after max retries.` All eight replayed
decisions were `user_error`; their corrected outer rewards are null.

| Original agent | Environment | Information | Task | Sample ID |
|---|---|---|---:|---|
| Gemini 2.5 Flash | eICU Original | Blocked | 2 | `6461fbcd-b139-4a08-94ea-49079a001dcb` |
| Gemini 2.5 Flash-Lite | eICU Original | Blocked | 2 | `47f080f4-a6cc-4391-995e-c10dee941828` |
| Gemini 2.5 Flash-Lite | eICU Original | Blocked | 89 | `fc8906e6-e120-4c4d-81d0-74426597e2d4` |
| Gemini 2.5 Pro | eICU Original | Blocked | 2 | `c7372f73-03c0-4239-a76f-5608cbdbbfa7` |
| Gemini 2.5 Pro | eICU Star | Available | 2 | `022393bd-8dcd-4d38-bad6-f42545e9dbb5` |
| Gemini 2.5 Pro | MIMIC Original | Blocked | 16 | `660d241e-5e82-41fd-b16f-fed14eaab8ea` |
| Gemini 2.5 Pro | MIMIC Star | Blocked | 16 | `8c045b79-5f43-4b1c-8715-eaaca44e5387` |
| Gemini 3.5 Flash | eICU Star | Blocked | 89 | `76f0b99a-515d-4c07-9ace-8d13320762f8` |

The full reasons and evidence are preserved in the replay output. Most cite
premature termination, missing requested conditions, or goal changes.
The Flash-Lite task-2 explanation is internally inconsistent: it criticizes
asking the agent to locate schema independently while citing a rule that
requires independent schema discovery. That record is flagged for explanation
review, not asserted to be a confirmed human error. Its raw validator verdict
is preserved and it remains quarantined; no extra model voting was performed.

## Cost and evidence

The eight returned validator costs sum to **$0.0098075**. This is the
provider-reported response cost, not an assumption that missing historical
cost fields were zero. After the initial reporting delay, selected-key usage
increased from **$69.592085226** to **$69.601892726**. The settled difference,
**$0.0098075**, matches the returned costs. No replacement agent runs were made.

Correction artifacts:

```text
results/historical-corrections-20260907/
  source_manifest.json
  local_score_corrections.json
  corrected_cohort.jsonl
  summary.json
  billing.json
```

`corrected_cohort.jsonl` is an audit view with original-record references and
corrected rewards, not a replacement `run.py` checkpoint. Its summary links
the full replay manifest and results, including exact input records, source
code, config, original/new validation, costs, and before/after input hashes.

Replay directory:

```text
results/revalidation/historical-validator-repair-e796fb95d090b56f5f62fdc4fc5f674f637286127b304ae892f10b008f817d63/
```

Original raw checkpoints remain unchanged. The historical reports retain
their original tables with links to this correction notice.

## Verification

- 57 replay/config/real-CLI regression tests passed.
- Compilation and `git diff --check` passed.
- Actual replay completed 8/8 reviews; all eight raw verdicts are `user_error`.
- Resuming the completed config left `results.jsonl` byte-identical.
- All 36 raw checkpoint files referenced by the accepted cohort retain their
  original SHA-256 hashes.
