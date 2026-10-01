# Schema-prior and reasoning trajectory analysis

**Date:** 2026-09-04

**Scope:** IncreQA pilot tasks MIMIC-IV 20/16/125 and eICU 108/2/89

**Reporting:** Descriptive counts only; no p-values

## Executive findings

1. **Renaming does not uniformly reduce performance.** Gemini 3.8 Flash is
   unchanged at 4/6 versus 4/6 when schema information is available, while
   Gemma 4 26B-A4B improves from 2/6 to 4/6 on Star. The transformed schema
   can therefore be easier for some models and tasks.
2. **The unavailable-by-renaming interaction is visible only for Gemini 3.8
   Flash in this pilot.** Its rename penalty is zero with schema information
   but two successes under the blocked condition: Original 2/6 versus Star
   0/6. Other models are at a blocked floor and cannot test amplification.
3. **Larger model size does not produce a monotonic prior effect.** Gemma 4
   26B-A4B and 31B both score 6/24 and both score 0/12 blocked. Gemini 3.8
   Flash is strongest and uniquely retains Original blocked successes, but
   architecture, training, and model-family differences prevent a pure size
   claim.
4. **Explicit high reasoning hurts Flash-Lite in the matched experiment.**
   Provider default scores 5/24; high reasoning scores 0/24. High reasoning
   uses more turns, SQL calls, requests, tokens, and 2.45x the cost.
5. **Reasoning produces local corrections but no rewarded aha.** Several
   trajectories move from an identifier error to a valid schema or SQL
   response, but none reaches a correct final answer. Overthinking,
   unproductive clarification, repeated queries, and failure to propagate
   corrected facts are more prominent.
6. **Blocked does not leak the direct catalog, but it retains a membership
   oracle.** All `sqlite_master` attempts are denied. Ordinary SQL still
   distinguishes nonexistent tables, existing tables with wrong columns,
   and valid identifiers through detailed SQLite errors.

## Accepted experiment matrix

| Model/configuration | Original available | Original blocked | Star available | Star blocked | Overall |
|---|---:|---:|---:|---:|---:|
| Flash-Lite provider default, matched | 4/6 | 0/6 | 1/6 | 0/6 | 5/24 |
| Flash-Lite high reasoning v3 | 0/6 | 0/6 | 0/6 | 0/6 | 0/24 |
| Gemma 4 26B-A4B | 2/6 | 0/6 | 4/6 | 0/6 | 6/24 |
| Gemma 4 31B | 3/6 | 0/6 | 3/6 | 0/6 | 6/24 |
| Gemini 3.8 Flash | 4/6 | 2/6 | 4/6 | 0/6 | 10/24 |

The two Flash-Lite rows use the same model, tasks, 8192 completion-token
budget, tools, prompts, user simulator, and validator. The explicit
`reasoning_effort=high` setting is the intended treatment difference.

## Motivation 1: renamed-schema performance

Rename penalty is `Original successes - Star successes`; positive values
mean that renaming hurt.

| Model/configuration | Available penalty | Blocked penalty | Interpretation |
|---|---:|---:|---|
| Flash-Lite provider default | +3 | 0, floor | Star is harder even with information |
| Flash-Lite high reasoning | 0, floor | 0, floor | Not informative |
| Gemma 4 26B-A4B | -2 | 0, floor | Star is easier in available |
| Gemma 4 31B | 0 | 0, floor | No aggregate rename effect |
| Gemini 3.8 Flash | 0 | +2 | Rename hurts only when blocked |

This evidence rejects a universal claim that renaming itself lowers
performance. A defensible claim is narrower:

> For a capable model, renaming can remove useful Original-schema prior when
> identifiers are not supplied; with identifiers supplied, the same rename
> need not hurt.

Gemini 3.8 Flash supplies the cleanest outcome evidence for that mechanism.
Flash-Lite provider default supplies evidence that Star can also introduce
intrinsic difficulty even when information is available.

## Motivation 2: blocked information amplifies rename penalty

Only Gemini 3.8 Flash shows the intended pattern without a floor:

| Condition | Original | Star | Difference |
|---|---:|---:|---:|
| Available | 4/6 | 4/6 | 0 |
| Blocked | 2/6 | 0/6 | 2 |

Task-level blocked Original-only successes are MIMIC task 16 and eICU task 2.
No Star blocked task succeeds.

Gemma 26B-A4B, Gemma 31B, and both Flash-Lite configurations score zero in
both blocked schemas. Their zero rename penalty is not evidence of
robustness; it is an all-failure floor.

## Motivation 3: capacity and prior bias

### Outcome trend

| Model/configuration | Available | Blocked |
|---|---:|---:|
| Flash-Lite provider default | 5/12 | 0/12 |
| Flash-Lite high reasoning | 0/12 | 0/12 |
| Gemma 4 26B-A4B | 6/12 | 0/12 |
| Gemma 4 31B | 6/12 | 0/12 |
| Gemini 3.8 Flash | 8/12 | 2/12 |

The Gemma variants provide no monotonic size trend: total score and blocked
score are identical despite their different total/active parameter
structures. Gemini 3.8 Flash has both the highest available capability and
the only blocked retention, but it is a different model family.

### Original-identifier intrusion inside Star trajectories

| Model/configuration | Allowed: any intrusion | Blocked: any intrusion |
|---|---:|---:|
| Flash-Lite provider default, matched | 2/6 | 0/6 |
| Flash-Lite high reasoning | 2/6 | 2/6 |
| Gemma 4 26B-A4B | 2/6 | 1/6 |
| Gemma 4 31B | 2/6 | 2/6 |
| Gemini 3.8 Flash | 0/6 | 5/6 |

Gemini 3.8 Flash's blocked Star trajectories repeatedly probe exact Original
tables such as `diagnoses_icd`, `prescriptions`, `procedures_icd`, and
`medication`. All matching Star queries fail, and none receives reward.
This is stronger evidence of usable Original-schema prior than raw parameter
count alone.

## Matched reasoning experiment

### Performance and efficiency

| Metric over 24 canonical trajectories | Provider default | High reasoning | Change |
|---|---:|---:|---:|
| Reward | 5/24 | 0/24 | -5 |
| Conversations reaching `###END###` | 11/24 | 8/24 | -3 |
| Assistant turns | 528 | 617 | +89 |
| SQL calls | 206 | 251 | +45 |
| Redundant identical SQL calls | 30 | 29 | -1 |
| Empty assistant actions | 5 | 0 | -5 |
| API requests, including retries | 2,063 | 2,757 | +694 |
| Prompt tokens | 4,081,706 | 7,550,190 | +3,468,484 |
| Completion tokens | 264,436 | 877,620 | +613,184 |
| Reasoning tokens | 58,150 | 257,074 | +198,924 |
| Cost | $0.417297460 | $1.023940140 | +145.4% |

High reasoning eliminates empty actions after the explicit 8192-token output
budget is added, but that reliability improvement does not yield a task
success. It instead regresses every provider-default success:

- MIMIC tasks 20, 16, and 125, Original available.
- eICU task 108, Original available.
- MIMIC task 16, Star available.

### Five lost corrections

| Task-condition | Provider-default behavior | High-reasoning behavior |
|---|---|---|
| eICU 108, Original available | Discovers `microlab` and `vitalperiodic`, builds the temporal join, returns `3139532` | Continues guessing nonexistent tables |
| MIMIC 20, Original available | Corrects to the `icd_code + icd_version` join and returns 1 | Uses dictionary `ROW_ID` as the diagnosis linkage and returns 0 |
| MIMIC 16, Original available | Adds the catheter-clearance exclusion and returns 12.22 | Sums records, guesses `note`, filters `route`, returns null |
| MIMIC 125, Original available | Corrects `icd9_code` to `icd_code` and returns all three procedures | Finds the column but mistypes admission `27568122` as `275681222` |
| MIMIC 16, Star available | Discovers `costamount` and returns 12.22 | Repeats `cost`/`amount` guesses without schema recovery |

### Behavioral aha moments

An aha is counted only when reasoning explicitly revises an assumption and
the following SQL changes from an error to a valid result. High reasoning
contains several local examples:

- eICU Star available task 108 abandons `diagnoses`, searches for available
  lab tables, and obtains a valid `lab` schema result.
- eICU Star available task 89 moves from Original-style columns to
  `unit_id`, `fluid_balance_time`, and `fluid_label`.
- MIMIC Original available task 20 replaces failed code-column guesses with
  `ROW_ID` and returns actual dictionary IDs.
- MIMIC Original available task 125 discovers `icd_code` after schema
  inspection.

None becomes a rewarded answer. The corrections are local but do not
propagate through the complete task logic.

### Overthinking and perseveration

- MIMIC Star available task 20 produces 34,910 reasoning characters and 30
  assistant turns but only two SQL calls. It says it will “break this cycle”
  and then performs no changed action.
- MIMIC Star available task 125 repeats one `sqlite_master` query 10 times
  and a query using nonexistent `admitdate` nine times.
- MIMIC Original blocked task 16 produces 17,307 reasoning characters over
  25 turns but only three SQL calls.
- eICU Star available task 89 discovers schema details but remains attached
  to the wrong `fluid_balance` table.

The dominant high-reasoning failure mode is not lack of thought. It is
failure to convert corrected local beliefs into a compact, task-complete SQL
action.

## Star-to-Original regression

Across the 12 matched Flash-Lite Star trajectories:

| Metric | Provider default | High reasoning |
|---|---:|---:|
| First-SQL Original intrusion | 1/12 | 3/12 |
| Any Original intrusion | 2/12 | 4/12 |
| Recovery after intrusion | 2/2 | 0/4 |
| Generic-schema error | 10/12 | 12/12 |

Exact high-reasoning cases:

- MIMIC Star allowed task 16 uses Original `cost` and never recovers.
- MIMIC Star allowed task 125 repeatedly uses Original `admissions`.
- MIMIC Star blocked task 20 introduces Original `diagnoses_icd`.
- MIMIC Star blocked task 125 uses `admissions` three times, each receiving
  `no such table`, with no Star recovery.

This matched result supports a negative reasoning finding:

> High reasoning increases the number of trajectories that invoke
> Original-schema prior and reduces observed recovery after that intrusion.

Generic inventions such as `medications`, `order_items`,
`medication_events`, or `encounters` are reported separately and are not
misclassified as Original recall.

## What blocked access actually means

The accepted runs use SQL_ONLY in both available and blocked conditions.
Metadata helper tools are absent from both. The blocked condition additionally
denies SQLite catalogs/PRAGMAs and removes identifier-bearing guidance.

Matched Flash-Lite blocked trajectories:

| Metric | Provider default | High reasoning |
|---|---:|---:|
| Catalog-attempt trajectories | 8/12 | 6/12 |
| Catalog attempts | 15 | 6 |
| Successful catalog disclosures | 0 | 0 |
| Ordinary SQL membership calls | 86 | 116 |
| Existing-table recovery | 0/12 | 2/12 |
| Successful task reward | 0/12 | 0/12 |

High reasoning makes fewer direct catalog attempts but 30 more ordinary SQL
membership probes. It reaches existing Original tables in two trajectories,
but wrong columns prevent any successful data query or reward.

The defensible label is:

> **Catalog-blocked, identifier-free, ordinary SQL probing allowed.**

The condition is not literally schema-opaque because detailed
`no such table` and `no such column` errors expose a table/column membership
oracle.

## Limitations

- Each accepted cell is k=1.
- The user simulator runs at temperature 1.0, so task-level model flips also
  include a newly sampled conversation.
- Available versus blocked changes both catalog access and prompt guidance.
- Star transformation can alter intrinsic task difficulty, not only prior
  accessibility.
- Gemma 26B-A4B, Gemma 31B, and Gemini 3.8 Flash are not a controlled
  parameter-scaling series.
- Reasoning text is available only for the explicit high-reasoning v3 run;
  provider-default reasoning is observable through token counts and actions,
  not hidden-thought text.
- Local error-to-valid-query recovery is not equivalent to final task
  success.

## Recommended next design

1. Factor identifier-bearing guidance, direct catalog access, helper tools,
   and detailed error feedback independently.
2. Add a strict blocked arm that rejects schema-probing SQL before SQLite or
   returns uniform binary errors.
3. Keep Original and Star paired on the same task set.
4. Replay or seed user-simulator interactions when comparing agent settings.
5. Measure first-query Original intrusion, post-error persistence, recovery,
   repeated SQL, turns, reasoning tokens, and final reward.
6. Test low or medium reasoning before another high-reasoning run; high
   reasoning currently shows clear overthinking and action-suppression costs.

## Primary artifacts

- High reasoning v3:
  `results/gemini_2.5_flash_lite_reasoning_high_incre_pilot_v3/`
- Matched provider-default control:
  `results/gemini_2.5_flash_lite_provider_default_maxout8192_incre_pilot/`
- Invalid provider-default partial:
  `results/gemini_2.5_flash_lite_reasoning_high_incre_pilot/`
- Invalid high-reasoning/no-output-budget partial:
  `results/gemini_2.5_flash_lite_reasoning_high_incre_pilot_v2/`
- Gemini 3.8 Flash:
  `results/gemini_3.8_flash_incre_adapt_pilot/`
- Gemma 4 26B-A4B:
  `results/gemma_4_26b_a4b_incre_adapt_pilot/`
- Gemma 4 31B:
  `results/gemma_4_31b_incre_pilot/`
