# Gemini 2.5 Flash-Lite full-tool IncreQA results

## Summary

The official-user-simulator rerun completed **572/572 task-schema slots** with
**283 successes and 289 failures: 49.48% success at k=1**. All four environments
have complete coverage, with no missing or duplicate accepted slots.

The run took **79 minutes 47.686 seconds** and incurred **$5.83818909 in
OpenRouter usage**, including unsuccessful simulation attempts. Tavily usage is
reported separately as **26 advanced-search credits**.

This report's primary result is the fresh official-user rerun completed on
2026-09-09, not the earlier modified-simulator run that scored 324/572 (56.64%).
No outcomes from that earlier pilot or full evaluation were reused.

## Research questions from the September 3 meeting

The study focuses on **IncreQA**, with **Gemini 3.8 Flash as the main backbone**.
This Gemini 2.5 Flash-Lite evaluation is supporting evidence for the tool-access
comparison; it is not a substitute for the main-backbone experiment. AdaptQA
and new paid model evaluations are outside this report.

| Motivation | Meeting hypothesis and comparison | Role of this report |
|---|---|---|
| 1: Schema renaming and tool access | Renaming Original to Star may reduce accuracy through prior schema-name bias. With metadata available, compare full tools against SQL-only, including Original/Star table and column usage in Star trajectories. | Measure full-tool Original/Star performance and name usage; compare against the historical matched SQL-only baseline with provenance limits. |
| 2: Metadata availability | Within SQL-only, the Original-to-Star decrease should be larger with metadata unavailable than with it available. | The full-tool run has metadata available throughout; it cannot test this interaction. |
| 3: Model size and prior knowledge | Under Motivation 1's design, larger explicitly sized open-weight models may show stronger prior-name bias. | One closed model does not test a parameter-size trend. Keep this as a separate model-family comparison. |

The meeting's earlier observation of a Star performance drop is a hypothesis
to check under full tools, not a result to impose on this rerun. Here, Star
scores higher than Original in both databases.

## Evaluation setup

| Setting | Value |
|---|---|
| Benchmark | IncreQA; MIMIC-IV and eICU, each with Original and Star schemas |
| Coverage | 145 MIMIC-IV tasks and 141 eICU tasks, each evaluated in both schemas |
| Repetitions | k=1 per task-schema slot; 572 accepted outcomes over 286 underlying tasks |
| Agent | `openrouter/google/gemini-2.5-flash-lite`, temperature 0 |
| User simulator | `openrouter/google/gemini-2.5-flash-lite`, temperature 1, `nested-reflection` |
| Validator | `openrouter/google/gemini-2.5-flash`, one validation trial |
| Embeddings | `openrouter/openai/text-embedding-3-small` |
| Tools | `sql_execute`, `table_search`, `column_search`, `value_substring_search`, `value_similarity_search`, `web_search` |
| Information access | `metadata_access=allowed`, `schema_guidance=benchmark` |
| SQL error feedback | `failure_feedback=detailed` |
| Scoring | SQL-result any-hit scoring, `reward_scope=any`; not answer-tag accuracy |
| Limits | `max_agent_turns=30`, `timeout=600`, `max_retry=10` |
| Job timeout | `run_timeout=43200` seconds per environment job |
| Parallelism | Initially 8 trajectories; continued with 4 environments x 3 workers = 12 |

The user simulator's `src/envs/user.py` matches the pinned official file:

```text
SHA256 076edd1bdb04c6c46dc06eea471811167e4cd9fbf1cbad00a366e529b1fea510
```

All seven baseline runtime-file hashes were unchanged during this rerun.
Models, prompts, scoring and per-task limits were not rewritten to obtain
coverage. The established Flash-Lite user and small embedding model were
retained. "Official user" describes the simulator control flow, not an assertion
that every model, transport and scoring setting reproduces the paper defaults.

## Motivation 1: Full-tool results by environment

| Database | Schema | Successes | Failures | Accepted / expected | Success rate |
|---|---|---:|---:|---:|---:|
| MIMIC-IV | Original | 73 | 72 | 145/145 | 50.34% |
| MIMIC-IV | Star | 77 | 68 | 145/145 | 53.10% |
| eICU | Original | 63 | 78 | 141/141 | 44.68% |
| eICU | Star | 70 | 71 | 141/141 | 49.65% |
| **Total** | **Both** | **283** | **289** | **572/572** | **49.48%** |

Across databases, Original scored **136/286 (47.55%)** and Star scored
**147/286 (51.40%)**, a descriptive difference of **+3.85 percentage points**.
Within MIMIC-IV the difference was +2.76 points; within eICU it was +4.96 points.
Differences are calculated before rounding.

Paired Original-to-Star changes use the same task ID within each database:

| Database | Pairs | Both succeed | Both fail | Original fails / Star succeeds | Original succeeds / Star fails |
|---|---:|---:|---:|---:|---:|
| MIMIC-IV | 145 | 51 | 46 | 26 | 22 |
| eICU | 141 | 42 | 50 | 28 | 21 |
| **Total** | **286** | **93** | **96** | **54** | **43** |

These are single-run task-level observations. k=1 does not estimate per-task
reliability, and the two schema variants are paired copies of the underlying
tasks rather than 572 independent questions. No p-values or population-level
claims are reported.

### Full tools versus the historical SQL-only baseline

The metadata-available comparison matches **572/572 task-schema slots**.
Instructions, gold SQL and gold answers match for every pair. The baseline is
the saved first-valid SQL-only cohort, not the earlier modified-simulator
full-tool cohort.

| Environment | SQL-only successes | Full-tool successes | Full minus SQL-only | Rescues | Regressions |
|---|---:|---:|---:|---:|---:|
| MIMIC-IV Original | 48/145 (33.10%) | 73/145 (50.34%) | +17.24 pp | 41 | 16 |
| MIMIC-IV Star | 27/145 (18.62%) | 77/145 (53.10%) | +34.48 pp | 57 | 7 |
| eICU Original | 8/141 (5.67%) | 63/141 (44.68%) | +39.01 pp | 60 | 5 |
| eICU Star | 14/141 (9.93%) | 70/141 (49.65%) | +39.72 pp | 61 | 5 |
| **Total** | **97/572 (16.96%)** | **283/572 (49.48%)** | **+32.52 pp** | **219** | **33** |

A rescue is a historical SQL-only failure paired with a full-tool success;
a regression is the reverse. Another 64 slots succeed in both runs and 256
fail in both. These terms describe paired outcomes, not a recovery within one
conversation.

Pooled Original-to-Star performance changes from **56/286 -> 41/286**
(19.58% -> 14.34%, -5.24 pp) under historical SQL-only to
**136/286 -> 147/286** (47.55% -> 51.40%, +3.85 pp) under full tools.
The historical SQL-only drop is concentrated in MIMIC-IV: eICU already has a
positive Star-minus-Original difference. Do not describe renaming as uniformly
harmful across both databases.

This supports the meeting's full-tool follow-up descriptively: full tools have
higher observed success in all four environments, and no aggregate Star
penalty is observed in this rerun. It is **not a controlled tools-only causal
estimate**. The SQL-only cohort was generated on August 26/28/29, while the
full-tool cohort was generated on September 9. It reuses 193 first-valid
completions from prior k=3 files and 379 later k=1 outcomes. Selection was not
best-of-three, but first saved valid completion is not a randomized first trial.
Complete historical simulator/runtime equivalence is not established, and
conversations were regenerated rather than replayed. Nominal model,
temperature, feedback and guidance settings do not remove those differences.

### Original and Star table/column names inside full-tool Star trajectories

The posthoc audit covers **all 286 accepted Star trajectories**, including
score-zero outcomes. It uses exact case-normalized schema membership:
**Original-only**, **Star-only**, **shared**, or **unknown**, separately for
tables and columns. Column membership is database-wide, not a claim that a
column belongs to the queried table or an inferred rename mapping.

The primary table below counts physical references written in `sql_execute`
queries. Repeated references count repeatedly as occurrences. Calls and
trajectories use table-or-column unions, so a query containing both is counted
once in those columns.

| Star environment | Accepted trajectories | SQL calls | Original-only table occurrences | Original-only column occurrences | Star-only table occurrences | Star-only column occurrences | SQL calls with Original-only names | Trajectories with Original-only SQL names |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MIMIC-IV Star | 145 | 509 | 6 | 111 | 1,258 | 4,382 | 79/509 | 20/145 |
| eICU Star | 141 | 436 | 1 | 2 | 598 | 3,757 | 3/436 | 3/141 |
| **Total** | **286** | **945** | **7** | **113** | **1,856** | **8,139** | **82/945 (8.68%)** | **23/286 (8.04%)** |

Star-only names appear in **939/945 SQL calls** and **258/286 trajectories**.
Original-only and Star-only categories can co-occur within one query; they
are not mutually exclusive call or trajectory partitions.

Adding explicit schema arguments in `column_search` and value-search tools
gives this broader, separately reported measure:

| Scope, accepted Star trajectories | Tool calls | Original-only table / column occurrences | Star-only table / column occurrences | Calls with Original-only names | Trajectories with Original-only names |
|---|---:|---:|---:|---:|---:|
| SQL plus all other tools | 2,063 | 11 / 113 | 2,608 / 8,366 | 86/2,063 | 27/286 (9.44%) |

The additional four Original-only references are eICU table arguments.
The all-tool count is not a like-for-like SQL-call denominator; it must not be
used to imply a cross-mode decrease merely because full tools expose more
ways to reference a name. This report's historical tool comparison is a
performance comparison; it does not claim a measured reduction in name
intrusion versus SQL-only using incompatible legacy counting rules.

Counting exclusions and uncertainty:

- Aliases, CTE names, derived output names, comments, prose and clinical string
  values are not physical Original-name intrusions.
- Shared names are separate: the SQL subset contains 212 shared table and
  227 shared column occurrences. Unknown names are also separate: 39 table and
  512 column occurrences, appearing in 193 SQL calls.
- The SQL denominator retains **3 parse-failure calls** and **26 calls with
  parse/scope uncertainty in total**, including those 3. Unresolved candidate
  references are not counted as confirmed physical references or treated as
  clean negative evidence.
- One metadata-exploration call is kept separate. Ignored `table_search` input
  is not counted; explicit `column_search.table_names` is counted because that
  tool accesses the requested table.

Two concrete examples from the eICU-Star final checkpoint:

| Task | Sample | Evidence | Observation |
|---|---|---|---|
| 119 | `762cbed6-a1e3-475c-92d4-b6695519dbe1` | Line 154, message index 26, SQL `JOIN patient p` | Original-only table `patient`; matching response: `no such table: patient` |
| 31 | `defa0d35-0808-4c98-86bb-d48634ae5013` | Line 45, message index 18, SQL `SUM(T1.cost)` | Original-only column `cost`; matching response: `no such column: T1.cost` |

Message indices are zero-based. These examples show actual references and
matched error responses, not a substring count of quoted schema names.
Original-only names remain observable even when aggregate Star performance
does not decline. Ten of the 27 all-tool intrusion trajectories have stored
reward 1; any-hit scoring means this is co-occurrence, not proof of recovery
after the offending call. Name occurrence alone does not prove memorization
or identify the causal source of the spelling.

## Motivation 2: What this run does not establish

There is no metadata-unavailable arm in this full-tool rerun. Motivation 2
requires SQL-only measurements in four cells: Original/available,
Star/available, Original/unavailable and Star/unavailable. Its descriptive
target is whether the Original-minus-Star performance gap is larger in the
unavailable condition.

Historical SQL-only available and unavailable runs exist, but their unavailable
condition also used identifier-free guidance rather than benchmark guidance.
They should not be described as a pure metadata-only intervention without
accounting for that difference. The present full-tool score cannot resolve the
meeting's ambiguous metadata trend.

## Motivation 3: Separate size-controlled comparison

The meeting proposes comparing explicitly sized models within an open-weight
family using Motivation 1's task, schema and tool matrix. Its Qwen examples are
`qwen/qwen3.8-27b` and `qwen/qwen3.8-2.4t-a95b`; these are proposed candidates
from the meeting, not endpoints verified or experiments executed for this
report. For a dense/MoE comparison, record both total and active parameter counts
rather than treating the two as interchangeable measures of size.

Flash-Lite versus Flash is not a disclosed-parameter-size comparison. Neither
this run's success rates nor Original-name occurrences alone establish that
larger models have stronger prior knowledge bias.

The meeting reference, [arXiv:2604.24827](https://arxiv.org/abs/2604.24827),
studies factual-recall probes as a coarse signal of parameter count. Its
abstract does not itself demonstrate a causal relationship between model size
and schema-name intrusion in EHR tasks. Motivation 3 remains an empirical
question for the controlled model comparison.

## Attempts, rejected simulations and agent failures

The checkpoint history contains **786 distinct attempts**. Of these, 572 were
accepted as valid trajectories and 214 were rejected with `user_error`.
Rejected simulations are retained in the audit trail; they are not converted
into agent failures to fill coverage and are not in the 572-outcome denominator.
Thus, 49.48% is success among accepted simulations, not among all raw attempts.
The accepted set contains 571 `no_error` records and one scored
`agent_timeout` failure (eICU Original task 98); accepted does not mean that
every trajectory ended without an agent error.

| Environment | Saved attempts | Accepted outcomes | Rejected simulations |
|---|---:|---:|---:|
| MIMIC-IV Original | 197 | 145 | 52 |
| MIMIC-IV Star | 198 | 145 | 53 |
| eICU Original | 209 | 141 | 68 |
| eICU Star | 182 | 141 | 41 |
| **Total** | **786** | **572** | **214** |

The 289 accepted score-zero trajectories comprise:

- **234 terminal score-zero trajectories**, labeled `terminal_sql_mismatch`
  in the saved analysis.
- **55 nonterminal trajectories**.

This classification separates an unsuccessful valid agent trajectory from an
invalid user simulation. It does not equate a missing answer tag with an
IncreQA SQL-result failure. The terminal count is reproduced by detecting a
user `###END###` sentinel in a score-zero trajectory; it is an operational
outcome category, not an independently diagnosed SQL root cause.

All 786 checkpointed attempts have sample-linked diagnostic files, totaling
41,592 events. Eight additional partial diagnostic files from interrupted
in-flight attempts are preserved separately and are not added to the 786 count.
Repeated checkpoint snapshots contain 855 rows before deduplication; 69
identical repeated snapshots account for the difference from 786 attempts.

One pre-existing aggregate discrepancy is retained rather than silently
rewriting the analysis: raw all-attempt messages contain 2,517 `sql_execute`
entries, while `analysis.json.tools.sql_execute` records 2,516. Its cause is
not established. The naming tables above are independently computed from
accepted Star trajectories only, with their explicit 945-SQL-call denominator.

## Cost and execution time

| Item | Measurement |
|---|---:|
| OpenRouter usage before | $92.482596181 |
| OpenRouter usage after | $98.320785271 |
| **Incremental OpenRouter cost** | **$5.83818909** |
| Cost per accepted outcome, including rejected attempts | $0.010207 |
| Start, UTC | 2026-09-09 14:35:49.198 |
| Finish, UTC | 2026-09-09 15:55:36.884 |
| Elapsed, including concurrency transition | 79 minutes 47.686 seconds |

The account usage delta is the cost total. Saved per-role accounting is partial:

| Role | Known cost | Missing or incomplete accounting |
|---|---:|---|
| Agent | $2.69384365 | 43 unknown agent-cost entries |
| User simulator | $2.18143707 | 69 incomplete user totals |
| Validator | $0.83090780 | 0 unknown validator-cost entries |

These partial role totals must not be zero-filled or substituted for the account
delta. The OpenRouter amount does not price Tavily credits.

There were **13 successful web-search tool responses**, corresponding to
**26 advanced-search credits**. At run completion, Tavily's delayed meter showed
262 -> 272 (+10); that historical snapshot remains in `analysis.json`. The
subsequent A/B run's baseline, recorded at 2026-09-09 18:47:41.585 UTC, shows
288 credits, consistent with 262 + 26. This report records that reconciliation
without overwriting the original snapshot.

## Preservation and interpretation

At the 8-to-12-worker transition, 52 accepted outcomes and all 69 saved attempts
were retained byte-identically. All 97 files in the initial rerun root remained
unchanged. The transition reused only outcomes from this official-user rerun,
not older modified-simulator results.

The saved final summary reports return code 0 for every environment job, complete
coverage, and empty missing-task, duplicate-task and coverage-error lists.
The existing run audit also records native result-schema validation and the
runtime-file hash checks.

For historical context only:

| Cohort | Successes / accepted | Success rate | OpenRouter cost |
|---|---:|---:|---:|
| Earlier modified-simulator full run, including reused pilot | 324/572 | 56.64% | $6.59140698, including pilot |
| **Fresh official-user rerun, primary result** | **283/572** | **49.48%** | **$5.83818909** |

The observed difference is -41 successes, or -7.17 percentage points. It is not
a causal estimate of the simulator change: the older cohort mixed pilot and
repaired-simulator sources, while the fresh run regenerated conversations and
used a different concurrency schedule. Keep the cohorts separate. This
full-tool-only rerun also does not, by itself, establish an improvement over
SQL-only or isolate the contribution of any individual tool.

## Evidence and reproduction references

The paths below identify local audit artifacts relative to the
`EHR-ChatQA-naming-audit` worktree. Raw trajectories, diagnostic transcripts and
runtime/config changes are not bundled with this report-only commit. The report
commit alone is not a complete runnable snapshot of the experiment.

Final configuration:

```text
experiments/gemini25fl-full-incre-official-simulator-rerun-p12.toml
```

Recorded continuation command, for provenance rather than a request to rerun:

```bash
.venv/bin/python -B experiment_runner.py experiments/gemini25fl-full-incre-official-simulator-rerun-p12.toml --resume
```

Final result root:

```text
results/config-runner/gemini25fl-incre-full-rerun-p12-20260909-07ab1ea4d9b59574e58806b6f73ba7ee61679c415bfe96a4bbeea23b4dadd233
```

- `summary.json`: per-job return codes and expected/accepted task coverage.
- `analysis.json`: environment scores, exact checkpoint paths, attempt and
  failure counts, costs, diagnostic index and preservation verification.
- `manifest.json`: resolved experimental settings and source provenance.
- `parallel-transition.json`: preserved initial root and transition evidence.
- `launch.json`: continuation command, seed hashes and execution metadata.
- `checkpoints/`: native results and diagnostic records, including rejected
  simulation attempts; the diagnostic index also references the initial root.

Additional records:

- `results/gemini25fl-incre-full-rerun-20260909-baseline.json`: initial runtime
  hashes and billing baseline.
- `results/gemini38-incre-ab-rerun-20260909-baseline.json`: later Tavily reading
  of 288 credits, used only for the billing reconciliation.
- Earlier cohort: `results/gemini25fl-full-incre-eval-report.md` in the original
  `EHR-ChatQA` worktree; its raw results remain separate.
- Historical SQL-only selection: original-worktree
  `temp/motivation-analysis/analyze_full_25fl_identifiers.py:118-165`.
  `result_paths` and `first_valid_records` combine matching
  `results/increqa32_k3/*.jsonl` files with
  `results/motivation_k1_flash_lite/incre-{mimic,eicu}-{original,star}-allowed/`.
  Files are sorted by filename timestamp and filename; the first non-null
  reward per task ID is retained. `results/motivation_experiment_report.md`,
  section 4.3, supplies the historical IncreQA table.
- Naming audit input:
  `results/flashlite-official-report-naming-audit/inputs/full-index.json`.
  It references the four exact final checkpoints from `analysis.json`.
- Naming audit outputs:
  `results/flashlite-official-report-naming-audit/full-a/` and `full-b/`.
  The unchanged `naming_audit` CLI completed twice with exit code 0; all seven
  output files were byte-identical, and input checkpoint/database hashes were
  unchanged. `calls.jsonl` retains each reference, classification, exclusion,
  query and source coordinate; `trajectories.jsonl` retains stored rewards.
  SQL-restricted full-tool naming totals filter `calls.jsonl` to Star
  environments and `name=sql_execute`, then count `primary=true` occurrences.
