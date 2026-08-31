# Motivation experiment report

**Updated:** 2026-08-30
**Status:** Pilot suite complete; Gemini 2.5 Flash-Lite full k=1 complete

## 1. Experiment map

| Experiment | Agent | Flow | Tasks | Conditions | Trials | Valid trajectories | Purpose |
|---|---|---|---:|---:|---:|---:|---|
| Full motivation run | Gemini 2.5 Flash-Lite | IncreQA + AdaptQA | 366 | 4 | 1 | 1,464/1,464 | Full-task lower-bound result |
| Four-model cost pilot | 2.5 Flash-Lite / 2.5 Flash / 3.5 Flash / 2.5 Pro | IncreQA | 6 | 4 | 1 | 24/model | Cost and candidate-model screening |
| 3.5 Flash-Lite pilot | Gemini 3.5 Flash-Lite | IncreQA | 6 | 4 | 1 | 24/24 | New low-cost backbone screening |
| 3.5 Flash AdaptQA pilot | Gemini 3.5 Flash | AdaptQA | 6 | 4 | 1 | 24/24 | Strong-model AdaptQA floor check |
| Star trajectory analysis | Five Gemini backbones | IncreQA | 6 | Star only | 1 | 60 | Original-schema prior analysis |
| 3.5 Flash Star analysis | Gemini 3.5 Flash | IncreQA + AdaptQA | 12 task-condition pairs | Star only | 1 | 24 | Clean mechanism comparison |

## 2. Shared configuration

| Item | Value |
|---|---|
| Agent strategy | Tool calling |
| User simulator | Gemini 2.5 Flash-Lite, temperature 1.0 |
| Validator | Gemini 2.5 Flash, temperature 0.0 |
| Agent temperature | 0.0 |
| Tool mode | SQL only |
| Failure feedback | Detailed |
| Embeddings | Disabled |
| Value similarity search | Disabled |
| Web search | Disabled |
| Max agent turns | 30 |
| Max user-simulation retries | 10 |
| Per-task timeout | 600 seconds |

| Schema-information condition | Metadata | Prompt guide |
|---|---|---|
| Available | Allowed | Benchmark identifier-bearing guide |
| Unavailable | Blocked | Identifier-free guide |

> The current PoC tests **schema-information availability**, not metadata access in isolation.

## 3. Dataset and cell counts

| Flow | MIMIC-IV | eICU | Tasks | Four conditions |
|---|---:|---:|---:|---:|
| IncreQA | 145 | 141 | 286 | 1,144 trajectories |
| AdaptQA | 40 | 40 | 80 | 320 trajectories |
| **Total** | **185** | **181** | **366** | **1,464 trajectories** |

| Cell factor | Values |
|---|---|
| Flow | IncreQA / AdaptQA |
| Database | MIMIC-IV / eICU |
| Schema | Original / Star-renamed |
| Schema information | Available / unavailable |
| Total | 16 cells |

## 4. Gemini 2.5 Flash-Lite full k=1

### 4.1 Overall

| Item | Result |
|---|---:|
| Final coverage | 1,464/1,464 |
| Reused first-valid trajectories | 257 |
| Reused-record ordering | Earliest saved valid completion from concurrent prior k=3 artifacts; no explicit trial index |
| Newly executed trajectories | 1,207 |
| Overall successes | 104/1,464 |
| Overall SR-1 | 7.10% |
| Start | 2026-08-29 05:10:43 |
| Final repair complete | 2026-08-29 11:46:54 |
| Wall-clock | 6 h 36 min |
| Settled incremental API charge | $33.4905 |
| Incremental cost/new trajectory | $0.0277 |

### 4.2 Condition results

| Condition | Success | SR-1 |
|---|---:|---:|
| Original + information available | 57/366 | **15.57%** |
| Original + information unavailable | 5/366 | 1.37% |
| Star + information available | 41/366 | 11.20% |
| Star + information unavailable | 1/366 | **0.27%** |

| Aggregate | Success | SR-1 |
|---|---:|---:|
| Information available | 98/732 | **13.39%** |
| Information unavailable | 6/732 | **0.82%** |
| Original schema | 62/732 | 8.47% |
| Star-renamed schema | 42/732 | 5.74% |

### 4.3 IncreQA

| DB | Original + available | Original + unavailable | Star + available | Star + unavailable |
|---|---:|---:|---:|---:|
| MIMIC-IV | **48/145 (33.10%)** | 5/145 (3.45%) | 27/145 (18.62%) | 0/145 (0.00%) |
| eICU | 8/141 (5.67%) | 0/141 (0.00%) | **14/141 (9.93%)** | 1/141 (0.71%) |
| **Total** | **56/286 (19.58%)** | **5/286 (1.75%)** | **41/286 (14.34%)** | **1/286 (0.35%)** |

### 4.4 AdaptQA

| DB | Original + available | Original + unavailable | Star + available | Star + unavailable |
|---|---:|---:|---:|---:|
| MIMIC-IV | 0/40 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) |
| eICU | **1/40 (2.50%)** | 0/40 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) |
| **Total** | **1/80 (1.25%)** | **0/80 (0.00%)** | **0/80 (0.00%)** | **0/80 (0.00%)** |

### 4.5 Paired available vs unavailable analysis

| Analysis item | Setting |
|---|---|
| Unit | Same task paired within the same schema |
| Outcome | Binary first-valid k=1 success |
| Test | Two-sided exact McNemar test |
| Available-only | Success with information available; failure when unavailable |
| Unavailable-only | Failure with information available; success when unavailable |
| Significance threshold | `p < 0.05` |

#### Gemini 2.5 Flash-Lite full k=1

| Schema | Available | Unavailable | Difference | Available-only | Unavailable-only | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|
| Original | **57/366 (15.57%)** | 5/366 (1.37%) | **+14.21%p** | 56 | 4 | **9.08×10⁻¹³** |
| Star-renamed | **41/366 (11.20%)** | 1/366 (0.27%) | **+10.93%p** | 41 | 1 | **1.96×10⁻¹¹** |

#### Gemini 3.5 Flash paired pilot

| Schema | Available | Unavailable | Difference | Available-only | Unavailable-only | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|
| Original | 10/12 (83.3%) | 7/12 (58.3%) | +25.0%p | 4 | 1 | 0.375 |
| Star-renamed | **11/12 (91.7%)** | 0/12 (0.0%) | **+91.7%p** | 11 | 0 | **0.00098** |

| Evidence statement | Status |
|---|---|
| Available information improves 2.5 Flash-Lite performance | Supported on both schemas |
| Available information improves strong-model Star performance | Supported |
| Strong-model Original difference is significant in the 12-pair pilot | Not supported; pilot is underpowered |
| Star blocked failure is explained by base model incapability | Rejected by Star-available positive control |
| Available condition can be removed to reduce cost | No; it is the positive control required for interpretation |

| Cost-constrained design option | Interpretation value |
|---|---|
| Remove available conditions | Invalidates the causal interpretation of blocked failures |
| Keep all four conditions at k=1 | Preferred minimum design |
| Reduce task count but preserve paired conditions | Valid pilot-stage compromise |
| Prioritize Star available/unavailable pairs | Preserves the primary renamed-schema test |
| Use a smaller Original control subset | Possible secondary compromise |

> These results identify a **schema-information availability effect** because
> metadata access and the identifier-bearing prompt guide change together.

### 4.6 Paired Original vs Star-renamed analysis

| Analysis item | Setting |
|---|---|
| Unit | Same task paired between Original and Star within the same information condition |
| Outcome | Binary first-valid k=1 success |
| Test | Two-sided exact McNemar test |
| Difference | Star SR minus Original SR |
| Retention | Star SR divided by Original SR |

#### Gemini 2.5 Flash-Lite full k=1

| Information | Original | Star-renamed | Difference | Retention | Original-only success | Star-only success | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|---:|
| Available | **57/366 (15.57%)** | 41/366 (11.20%) | -4.37%p | 71.9% | 43 | 27 | 0.0722 |
| Unavailable | 5/366 (1.37%) | 1/366 (0.27%) | -1.09%p | 20.0% | 5 | 1 | 0.2188 |

#### Gemini 3.5 Flash paired pilot

| Information | Original | Star-renamed | Difference | Retention | Original-only success | Star-only success | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|---:|
| Available | 10/12 (83.3%) | **11/12 (91.7%)** | +8.3%p | 110.0% | 1 | 2 | 1.0000 |
| Unavailable | **7/12 (58.3%)** | **0/12 (0.0%)** | **-58.3%p** | **0.0%** | 7 | 0 | **0.0156** |

| Schema-comparison evidence | Interpretation |
|---|---|
| 2.5 Flash-Lite available Original vs Star | Modest 4.37%p gap; not significant at 0.05 |
| 2.5 Flash-Lite unavailable Original vs Star | Both conditions are near the model floor |
| 3.5 Flash available Original vs Star | Renaming causes no observed penalty when schema information is available |
| 3.5 Flash unavailable Original vs Star | Significant 58.3%p Star collapse while Original retains 58.3% |
| Strong-model interaction | Public-schema prior is useful on Original, but does not transfer to renamed Star |

## 5. AdaptQA failure analysis

### 5.1 Gemini 2.5 Flash-Lite full k=1

| Outcome | Count | Share of 320 |
|---|---:|---:|
| Max-turn before final evaluation | **177** | **55.3%** |
| Conversation ended without answer tag | **134** | **41.9%** |
| Tagged answer was wrong | 8 | 2.5% |
| Correct tagged answer | 1 | 0.3% |

| Derived item | Result |
|---|---:|
| Failures before answer-value comparison | 311/319 (97.5%) |
| Evaluable tagged answers | 9/320 |
| Correct among tagged answers | 1/9 |

### 5.2 Gemini 3.5 Flash AdaptQA pilot

| Outcome | Count | Share of 24 |
|---|---:|---:|
| Correct tagged answer | **13** | **54.2%** |
| Max-turn before final evaluation | 10 | 41.7% |
| Conversation ended without answer tag | 1 | 4.2% |
| Tagged answer was wrong | 0 | 0.0% |

| Exact matched comparison | Success | SR-1 |
|---|---:|---:|
| 2.5 Flash-Lite on the same 24 task-condition pairs | 0/24 | 0.0% |
| 3.5 Flash | **13/24** | **54.2%** |

## 6. Four-model IncreQA cost pilot

### 6.1 Pilot task set

| DB | Task IDs |
|---|---|
| MIMIC-IV | 20, 16, 125 |
| eICU | 108, 2, 89 |

### 6.2 Performance and request-ledger cost

| Agent | Success | SR-1 | Request-ledger cohort cost | Cost/valid trajectory |
|---|---:|---:|---:|---:|
| Gemini 2.5 Flash-Lite | 2/24 | 8.3% | $0.4622 | $0.0193 |
| Gemini 2.5 Flash | 6/24 | 25.0% | $0.9957 | $0.0415 |
| Gemini 3.5 Flash | **15/24** | **62.5%** | $3.0835 | $0.1285 |
| Gemini 2.5 Pro | 6/24 | 25.0% | $8.2652 | $0.3444 |

| Billing reconciliation | Amount |
|---|---:|
| Sum of request-level `usage.cost` | $12.8065 |
| Exact key-usage delta | **$12.7277** |
| Difference | $0.0788 (0.619%) |

### 6.3 Pro reasoning

| Item | Result |
|---|---:|
| Pro Agent calls | 386 |
| Completion tokens | 787,069 |
| Reasoning tokens | 668,382 |
| Reasoning/completion share | **84.9%** |
| Explicit reasoning budget | Not set |
| Repair | Five interrupted placeholders rerun; repair overhead included |

## 7. Follow-up pilots

### 7.1 IncreQA candidate comparison

| Agent | Success | SR-1 | Settled/observed cost | Cost/trajectory |
|---|---:|---:|---:|---:|
| 2.5 Flash-Lite | 2/24 | 8.3% | $0.4622 | $0.0193 |
| 3.5 Flash-Lite | 4/24 | 16.7% | **$0.1988** | **$0.0083** |
| 2.5 Flash | 6/24 | 25.0% | $0.9957 | $0.0415 |
| 3.5 Flash | 15/24 | **62.5%** | $3.0835 | $0.1285 |
| 2.5 Pro | 6/24 | 25.0% | $8.2652 | $0.3444 |

### 7.2 Gemini 3.5 Flash: IncreQA vs AdaptQA

| Condition | IncreQA | AdaptQA | Difference |
|---|---:|---:|---:|
| Original + available | 5/6 (83.3%) | 5/6 (83.3%) | 0.0%p |
| Original + unavailable | 4/6 (66.7%) | 3/6 (50.0%) | -16.7%p |
| Star + available | **6/6 (100%)** | 5/6 (83.3%) | -16.7%p |
| Star + unavailable | 0/6 (0.0%) | 0/6 (0.0%) | 0.0%p |
| **Total** | **15/24 (62.5%)** | **13/24 (54.2%)** | **-8.3%p** |

### 7.3 Gemini 3.5 Flash AdaptQA pilot cost

| Key | Charge |
|---|---:|
| Primary `OPENROUTER_API_KEY` | $4.3758 |
| Low-credit `OPENROUTER_API_KEY_1` | $0.3037 |
| **Total** | **$4.6795** |
| Cost/trajectory | $0.1950 |

## 8. Star trajectory identifier analysis

### 8.1 Full 2.5 Flash-Lite counting method

| Item | Definition |
|---|---|
| Scope | All 366 Star-available and all 366 Star-unavailable first-valid k=1 trajectories |
| Source | Complete `messages` transcript, including every `sql_execute` call and tool result |
| Parser | SQLGlot 27.14.0 with the SQLite dialect |
| Original table | AST `Table` node in the Original rename map but absent from the Star table set |
| Original column | AST `Column` node in the Original rename map but absent from the Star column set |
| Renamed Star table | AST `Table` node present only in the renamed Star table set |
| Shared identifiers | Names present in both Original and Star are excluded from prior counts |
| Occurrence | One AST node; repeated references in one query are counted repeatedly |
| Affected trajectory | At least one Original-only table or column reference |
| Repeated trajectory | The same Original-only identifier occurs at least twice |
| Missing-schema error | Tool result contains `no such table` or `no such column` |
| Recovery | After an Original-identifier error, a later renamed-Star-table query returns a non-error result |
| Valid data SQL | At least one non-metadata SQL query returns a non-error result |
| Count confidence | Table-node counts are strongest; unqualified column nodes can include output-alias references |

| Parse coverage | Available | Unavailable |
|---|---:|---:|
| Parsed queries / SQL queries | 3,518/3,538 (99.4%) | 2,944/2,947 (99.9%) |
| Parse failures | 20 | 3 |

### 8.2 Full 2.5 Flash-Lite Star comparison

| Metric | Information available | Information unavailable | Change |
|---|---:|---:|---:|
| Trajectories | 366 | 366 | — |
| Success | **41/366 (11.20%)** | **1/366 (0.27%)** | **-10.93%p** |
| SQL queries | 3,538 | 2,947 | -16.7% |
| Original-table occurrences | 327 | **419** | **+28.1%** |
| Original-column occurrences | 1,342 | 974 | -27.4% |
| Total Original-identifier occurrences | 1,669 | 1,393 | -16.5% |
| Queries containing an Original identifier | 593/3,538 (16.8%) | 560/2,947 (19.0%) | +2.2%p |
| Trajectories containing an Original identifier | 152/366 (41.5%) | 140/366 (38.3%) | -3.3%p |
| Trajectories repeating the same Original identifier | 114/366 (31.1%) | 103/366 (28.1%) | -3.0%p |
| Renamed-Star-table occurrences | **1,884** | 109 | **-94.2%** |
| Queries containing a renamed Star table | **1,245/3,538 (35.2%)** | 91/2,947 (3.1%) | **-32.1%p** |
| Missing-schema errors | 2,151 | **2,495** | **+16.0%** |
| Trajectories with a missing-schema error | 325/366 (88.8%) | 332/366 (90.7%) | +1.9%p |
| Recovery after an Original-identifier error | **48/135 (35.6%)** | 1/95 (1.1%) | **-34.5%p** |
| Trajectories with a valid data-SQL result | **138/366 (37.7%)** | 2/366 (0.5%) | **-37.2%p** |
| Max-turn trajectories | 223/366 (60.9%) | **251/366 (68.6%)** | +7.7%p |

| Full-run interpretation | Result |
|---|---|
| Does total Original-name occurrence increase after blocking? | No; complex column-rich queries terminate earlier |
| Does Original-table occurrence increase? | Yes, 327 → 419 (+28.1%) |
| Does the share of queries containing Original identifiers increase? | Yes, 16.8% → 19.0% |
| Does renamed-Star identifier use persist? | No, renamed-Star queries fall from 35.2% to 3.1% |
| Can the model recover after an Original-identifier error? | Recovery falls from 35.6% to 1.1% |
| Main mechanism | Failure to discover and transition to renamed-Star identifiers |

### 8.3 Full 2.5 Flash-Lite flow breakdown

| Flow / information | Success | Original table occurrences | Original column occurrences | Renamed-Star queries | Recovery | Valid data SQL | Max-turn |
|---|---:|---:|---:|---:|---:|---:|---:|
| IncreQA available | 41/286 | 291 | 1,026 | 963 | 44 | 114/286 | 171/286 |
| IncreQA unavailable | 1/286 | **321** | 818 | **84** | **1** | **2/286** | **202/286** |
| AdaptQA available | 0/80 | 36 | 316 | 282 | 4 | 24/80 | 52/80 |
| AdaptQA unavailable | 0/80 | **98** | 156 | **7** | **0** | **0/80** | 49/80 |

### 8.4 Top Original identifiers in the full 2.5 Flash-Lite Star run

| Type | Information available | Information unavailable |
|---|---|---|
| Tables | `admissions` 173; `patients` 52; `labevents` 26; `transfers` 17; `d_icd_diagnoses` 15 | `admissions` 181; `prescriptions` 91; `patients` 83; `diagnoses_icd` 18; `diagnosis` 14 |
| Columns | `hadm_id` 421; `charttime` 168; `admittime` 137; `subject_id` 96; `drug` 95 | `hadm_id` 304; `test_name` 203; `admittime` 122; `charttime` 59; `event_type` 27 |

### 8.5 Original vs Star trajectory mechanism

#### Gemini 2.5 Flash-Lite full k=1

| Schema / information | Success | Valid data-SQL trajectory | Missing-schema errors | Trajectories with missing error | Max-turn |
|---|---:|---:|---:|---:|---:|
| Original available | **57/366** | **171/366 (46.7%)** | 1,627 | 251/366 (68.6%) | 134/366 (36.6%) |
| Star available | 41/366 | 138/366 (37.7%) | 2,151 | 325/366 (88.8%) | 223/366 (60.9%) |
| Original unavailable | 5/366 | 10/366 (2.7%) | **2,611** | 331/366 (90.4%) | 244/366 (66.7%) |
| Star unavailable | **1/366** | **2/366 (0.5%)** | 2,495 | 332/366 (90.7%) | **251/366 (68.6%)** |

| Original identifiers observed inside Star trajectories | Star available | Star unavailable |
|---|---:|---:|
| Original-table occurrences | 327 | **419** |
| Original-column occurrences | 1,342 | 974 |
| Queries containing an Original identifier | 593/3,538 (16.8%) | **560/2,947 (19.0%)** |
| Trajectories containing an Original identifier | 152/366 (41.5%) | 140/366 (38.3%) |
| Renamed-Star-table queries | **1,245/3,538 (35.2%)** | 91/2,947 (3.1%) |
| Original-error trajectories | 135 | 95 |
| Recovery after an Original-identifier error | **48/135 (35.6%)** | 1/95 (1.1%) |

| Interpretation rule | Application |
|---|---|
| Original identifiers in Original DB | Valid schema use; not counted as prior errors |
| Original identifiers inside Star DB | Evidence of fallback to the public Original schema |
| Total Original occurrence | Does not rise because blocked trajectories terminate before column-rich queries |
| High-confidence table occurrence | Rises 327 → 419 (+28.1%) after information removal |
| Main difference | Available trajectories transition to renamed-Star names; unavailable trajectories do not recover |

#### Gemini 3.5 Flash paired pilot

| Information | Original success | Star success | Original identifiers inside Star | Missing-schema errors inside Star | Interpretation |
|---|---:|---:|---:|---:|---|
| Available | 10/12 | **11/12** | **0** | **0** | Renamed schema is solved after discovery |
| Unavailable | **7/12** | **0/12** | **55** | **247** | Original prior remains useful only on Original DB |

### 8.6 Five-model IncreQA pilot aggregate

| Star condition | Trajectories | Success | Original identifier occurrences | Affected trajectories | Missing table/column errors |
|---|---:|---:|---:|---:|---:|
| Information available | 30 | 11/30 | 72 | 15/30 | 101 |
| Information unavailable | 30 | **1/30** | **242** | 17/30 | **301** |

| Change after information removal | Result |
|---|---:|
| Original identifier occurrences | 72 → 242 (**3.36×**) |
| Missing table/column errors | 101 → 301 (**2.98×**) |
| Success | 36.7% → 3.3% |

> The five-model pilot shows a larger Original-occurrence increase than the
> full 2.5 Flash-Lite run. The pilot trend must not be substituted for the
> full-run model-specific count.

### 8.7 Model breakdown: Star + information unavailable

| Agent | Success | SQL queries | Original identifier occurrences | Affected trajectories | Same identifier repeated | Missing table/column errors |
|---|---:|---:|---:|---:|---:|---:|
| 2.5 Flash-Lite | 0/6 | 41 | 37 | 2/6 | 2/6 | 28 |
| 2.5 Flash | 0/6 | 77 | **122** | 4/6 | 4/6 | 71 |
| 3.5 Flash-Lite | 1/6 | 116 | 39 | 3/6 | 2/6 | 63 |
| 3.5 Flash | 0/6 | **167** | 30 | **6/6** | 1/6 | **128** |
| 2.5 Pro | 0/6 | 13 | 14 | 2/6 | 1/6 | 11 |

### 8.8 Gemini 3.5 Flash clean comparison

| Star condition | Flows | Trajectories | Success | Original identifier occurrences | Original-identifier errors | All missing-schema errors |
|---|---|---:|---:|---:|---:|---:|
| Information available | IncreQA + AdaptQA | 12 | **11/12** | **0** | 0 | 0 |
| Information unavailable | IncreQA + AdaptQA | 12 | **0/12** | **55** | 52 | **247** |

### 8.9 Observed Original-schema identifiers

| DB | Tables/columns observed in Star queries |
|---|---|
| MIMIC-IV | `patients`, `admissions`, `diagnoses_icd`, `d_icd_diagnoses`, `procedures_icd`, `d_icd_procedures`, `prescriptions`, `labevents`, `d_labitems`, `inputevents`, `chartevents`, `subject_id`, `hadm_id`, `admittime`, `long_title` |
| eICU | `patient`, `medication`, `diagnosis`, `microlab`, `intakeoutput`, `vitalperiodic` |

### 8.10 Representative 3.5 Flash MIMIC Star trajectory

| Step | Information available | Information unavailable |
|---|---|---|
| Initial schema query | `sqlite_master` returns Star tables | `sqlite_master` access prohibited |
| Next action | `PRAGMA` on `diagnosiscodes` and `admissiondiagnoses` | Tries `diagnoses_icd`, `patients`, `admissions`, `d_icd_diagnoses` |
| Recovery | Uses valid Star identifiers | Tries generic/OMOP names and metadata bypasses |
| SQL result | Finds 6 cirrhosis patients and 1 hepatic-encephalopathy overlap | Repeated `no such table` / authorization errors |
| End state | User verification completed | 30-turn limit reached |
| Reward | **1** | **0** |

## 9. Data-integrity repairs

| Experiment | Cell/task | Cause | Repair result |
|---|---|---|---|
| Full 2.5 Flash-Lite | Incre eICU Original + available, task 44 | Validator structured-output JSON was truncated | Valid trajectory, reward 0 |
| Full 2.5 Flash-Lite | Incre eICU Star + unavailable, task 65 | User error followed by truncated validator JSON | Valid trajectory, reward 0 |
| Four-model cost pilot | Five 2.5 Pro placeholders | Credit interruption | Clean rerun; cost included |

## 10. Current evidence and limits

| Item | Status |
|---|---|
| Renamed-schema degradation | Observed |
| Strong-model reproduction | Observed with Gemini 3.5 Flash |
| Original-schema prior in Star trajectories | Observed across all five backbones |
| Mechanism: schema guessing → missing errors → max turns | Observed |
| Full-task strong-model run | Not yet run |
| k=3 strong-model reliability | Not yet run |
| Non-Gemini backbone replication | Not yet run |
| Exact planned `table_search`/`column_search`-only removal | Not yet implemented |
| Value similarity/substring tools retained in removed condition | Not yet implemented |

## 11. Local raw-data locations

| Data | Path |
|---|---|
| Full 2.5 Flash-Lite k=1 | `results/motivation_k1_flash_lite/` |
| Four-model cost pilot | `/tmp/emr-motivation-cost-pilot-stratified/` |
| Pro repair | `/tmp/emr-motivation-cost-pilot-stratified-repair/` |
| 3.5 Flash-Lite pilot | `/tmp/emr-motivation-35fl-pilot/` |
| 3.5 Flash AdaptQA pilot | `/tmp/emr-motivation-35flash-adapt-pilot/` |
| Detailed cost report | `temp/motivation-cost-pilot/PILOT_REPORT.md` |
