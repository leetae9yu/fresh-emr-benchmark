# Gemini 3.8 Flash SQL-only IncreQA expanded pilot

**Date:** 2026-09-07
**Status:** Complete, 128/128 unique valid trajectories

## Scope

- One agent: `openrouter/google/gemini-3.8-flash`, temperature 0.0.
- IncreQA only; `sql_execute` is the only exposed tool.
- MIMIC-IV and eICU: 16 logical tasks each, paired on Original/Star schemas.
- Information available: metadata allowed + benchmark guidance.
- Information blocked: metadata blocked + identifier-free guidance.
- Detailed SQL feedback in both conditions; ordinary SQL probing remains possible.
- k=1; historical any-hit SQL scoring with the live-result correctness fixes.
- User: Gemini 2.5 Flash-Lite, temperature 1.0; validator: Gemini 2.5 Flash, n=1.
- 30 agent turns, 600-second conversation budget, 10 simulation retries; 4 concurrent cells, 1 task worker per cell.
- No full-tool mode, AdaptQA, extra agent models, or old-outcome reuse.

## Results

| Schema | Information available | Information blocked |
|---|---:|---:|
| Original | **29/32 (90.625%)** | **21/32 (65.625%)** |
| Star | **29/32 (90.625%)** | **0/32 (0%)** |

| Database/schema | Available | Blocked |
|---|---:|---:|
| MIMIC Original | 15/16 | 14/16 |
| MIMIC Star | 15/16 | 0/16 |
| eICU Original | 14/16 | 7/16 |
| eICU Star | 14/16 | 0/16 |

Overall: 79 successes / 128 valid outcomes. The equal available-condition
success totals and Original-only retention under blocking are consistent
with useful Original-schema prior. These descriptive k=1 results do not
separate catalog access from prompt guidance or prove that all success
comes from memorization rather than reasoning.

## Coverage and recovery

The initial pass produced 100 valid outcomes. Four identical-config resume
passes brought coverage to 120, 124, 127, and finally 128. Each resume retained
completed outcomes and ran only missing task-condition slots. Final coverage
checks found 16 unique trial-1 outcomes in each of eight jobs, with no
duplicate or missing task IDs.

There are 188 distinct saved attempts: 128 valid outcomes, 19 invalid
user-validator decisions, and 41 user-generation runtime failures. Runtime
failures involved empty user responses or malformed END tokens. These
failed simulations were retained with null reward, not counted as agent
failures. Resampling invalid simulations means the valid-only success rates
are conditional on the simulation acceptance process.

Started: 2026-09-07 12:46:39.880 UTC.
Finished: 2026-09-07 13:49:36.861 UTC.
Wall-clock including recovery: **62 minutes 56.981 seconds**.

## Cost

| Item | USD |
|---|---:|
| Selected-key usage before | 69.601892726 |
| Selected-key usage after | 77.993810501 |
| **Total incremental usage** | **8.391917775** |
| Cost per valid outcome, including invalid attempts | 0.065562 |
| Account credits remaining | 262.006189499 |
| Current key allowance remaining | 122.006189499 |

The final single-task recovery cost of $0.03984885 exactly matches the
corresponding key-usage increment. The total is below the $10 planning
allowance and includes all retries and recovery runs.

Role-level saved costs are incomplete: one agent-cost field and 24 user-cost
fields are unknown; 24 total-cost fields are consequently unknown. Known
subtotals are agent $8.05791085, user $0.16630349, validator $0.09673930.
Do not treat these subtotals as complete charges or fill unknown values with
zero. The total above uses the selected-key delta instead.

## Fixed sampling

Seed: `gemini38-sqlonly-incre-expanded-20260907-v1`. For each database,
rank all task IDs by SHA-256 of `seed|database|task_id` and take the lowest
16. Selection did not inspect prior rewards. Copy the same selected IDs to
Original and Star.

- MIMIC: 2, 25, 28, 29, 33, 54, 56, 62, 72, 99, 108, 112, 121, 126, 139, 143.
- eICU: 8, 30, 34, 55, 57, 77, 78, 81, 85, 86, 92, 94, 103, 106, 132, 136.

## Artifacts

Config: `experiments/gemini38-sqlonly-incre-128.toml`.
Baseline: `results/gemini38-sqlonly-incre-128-20260907-baseline.json`.

Result directory:

```text
results/config-runner/gemini38-sqlonly-incre-128-20260907-4f289695941bf33846635df542238c16c4610aceeec9abe8693eb741796faa70
```

It contains the resolved manifest, per-job configs/logs/checkpoints, final
coverage summary, and `analysis.json` with exact checkpoint references and
computed results. Code and config remained fixed across resume passes.
The cost watcher has been stopped. No additional experiments were started.
