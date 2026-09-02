# Value-similarity experiment report

**Updated:** 2026-09-02
**Status:** Gemini 2.5 Flash-Lite pilot and full available-condition run complete; Gemini 3.5 Flash matched pilot complete

## 1. Experiment map

| Experiment | Agent | Task scope | Arms | Valid outcomes | Purpose |
|---|---|---:|---|---:|---|
| Value-heavy pilot | Gemini 2.5 Flash-Lite | 12 IncreQA tasks, Original + Star | Reused SQL_ONLY + new SQL_VALUE | 24 SQL_VALUE | Feasibility and failure-mode screening |
| Full available-condition run | Gemini 2.5 Flash-Lite | All 286 IncreQA tasks, Original + Star | Reused SQL_ONLY + new SQL_VALUE | 572 SQL_VALUE | Describe paired outcome differences across both databases |
| Matched strong-model pilot | Gemini 3.5 Flash | Same 12 value-heavy tasks, Original + Star | Fresh SQL_ONLY + fresh SQL_VALUE | 48 total | Test whether tool use changes with model capability |

The experiments test the deployed interface, not an oracle retrieval setting.
`value_similarity_search` requires the agent to supply a table, column, query
value, and optional result count. A useful call therefore requires both valid
schema arguments and a useful semantic query.

## 2. Shared configuration

| Item | Value |
|---|---|
| Flow | IncreQA |
| Trials | k=1 |
| Schemas | Original and Star-renamed |
| Schema information | Available |
| Metadata policy | Allowed |
| Prompt guidance | Benchmark identifier-bearing guide |
| Failure feedback | Detailed |
| Agent strategy | Tool calling |
| Agent temperature | 0.0 |
| User simulator | Gemini 2.5 Flash-Lite, temperature 1.0 |
| Final validator | Gemini 2.5 Flash, temperature 0.0 |
| Maximum agent turns | 30 |
| Maximum simulation retries | 10 |
| Per-task timeout | 600 seconds |
| Embedding route | `openrouter/openai/text-embedding-3-small` |
| FAISS indices | Existing Original and Star indices reused |

### 2.1 Tool arms

| Arm | Exposed tools |
|---|---|
| SQL_ONLY | `sql_execute` |
| SQL_VALUE | `sql_execute`, `value_similarity_search` |

Both arms retain metadata access and benchmark guidance. The comparison
therefore asks whether adding value similarity helps when schema information
is available. It is not a schema-information ablation.

### 2.2 Analysis definitions

| Term | Definition |
|---|---|
| Success | Outer trajectory reward equals 1 |
| Valid outcome | Saved trajectory with non-null outer reward |
| Actual match | Tool response begins with `I found` |
| No match | Tool response begins with `No matches found` |
| Runtime error | Tool response begins with `Error performing similarity search` |
| Rescue | SQL_ONLY failure and SQL_VALUE success on the same task and schema |
| Regression | SQL_ONLY success and SQL_VALUE failure on the same task and schema |
| Paired test | Two-sided exact McNemar test over rescue/regression discordance |

Nominal p-values are reported at the cell and pooled levels. They are not
adjusted for multiple subgroup comparisons.

## 3. Value-heavy task set

The small pilots use tasks where the user-facing term may differ from the
stored clinical value, or where the target expands to several database values.

| Database | Task IDs | Representative grounding problem |
|---|---|---|
| MIMIC-IV | 0, 1, 3, 5, 95, 113 | `Hb` to `hemoglobin`; `ISDN` to `isosorbide dinitrate`; procedure abbreviations |
| eICU | 3, 7, 12, 20, 37, 94 | WBC measurement name; ARDS variants; treatment, diagnosis, and input-event names |

Each task is evaluated on its Original and Star-renamed schemas.

## 4. Gemini 2.5 Flash-Lite value-heavy pilot

The accepted pilot contains 24 SQL_VALUE outcomes over the 12-task set and
uses the corresponding existing SQL_ONLY k=1 outcomes as its baseline.

### 4.1 Results

| Cell | SQL_ONLY | SQL_VALUE |
|---|---:|---:|
| MIMIC Original | 1/6 | 0/6 |
| MIMIC Star | 0/6 | 1/6 |
| eICU Original | 0/6 | 0/6 |
| eICU Star | 0/6 | 0/6 |
| **Overall** | **1/24** | **1/24** |

| Paired item | Result |
|---|---:|
| SQL_ONLY-only success | 1 |
| SQL_VALUE-only success | 1 |
| Exact McNemar p-value | 1.0 |

### 4.2 Mechanism

| Metric | Result |
|---|---:|
| Value-search calls | 221 |
| SQL calls | 94 |
| Actual match responses | 2 |
| No-match responses | 219 |
| Runtime errors | 0 |
| Trajectories using value search | 23/24 |
| Value-search trajectories without SQL | 8/24 |

The sole SQL_VALUE success occurred on MIMIC Star task 1. The agent used
`medicationorders.medicationname` to resolve `ISDN` to
`isosorbide dinitrate`, then used that value in SQL.

The SQL_ONLY-only success was the corresponding MIMIC Original task. In the
SQL_VALUE trajectory, the agent repeatedly supplied non-indexed columns such
as `medicationname` and `drugname` instead of `prescriptions.drug`, obtained
no matches, and never executed SQL.

The pilot did not show an aggregate benefit. Its dominant observed failure was
invalid table-column selection followed by repeated no-match calls.

## 5. Gemini 2.5 Flash-Lite full available-condition run

### 5.1 Coverage

| Item | Result |
|---|---:|
| Logical treatment outcomes | 572 |
| Valid treatment outcomes | 572/572 |
| Saved attempts | 657 |
| Invalid simulation attempts | 85 |
| Repaired missing tasks | MIMIC Original 141; MIMIC Star 111 |

The SQL_ONLY arm reuses the existing k=1 available-condition outcomes. The
MIMIC Original baseline includes earliest saved valid completions reused from
the prior k=3 artifacts, matching the existing motivation report convention.

### 5.2 Cell results

| Cell | SQL_ONLY | SQL_VALUE | Difference | SQL_ONLY-only | SQL_VALUE-only | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|
| MIMIC Original | 48/145 (33.10%) | 26/145 (17.93%) | **-15.17%p** | 31 | 9 | **0.000680** |
| MIMIC Star | 27/145 (18.62%) | 13/145 (8.97%) | **-9.66%p** | 20 | 6 | **0.00936** |
| eICU Original | 8/141 (5.67%) | 20/141 (14.18%) | **+8.51%p** | 5 | 17 | **0.01690** |
| eICU Star | 14/141 (9.93%) | 17/141 (12.06%) | +2.13%p | 10 | 13 | 0.67764 |
| **Overall** | **97/572 (16.96%)** | **76/572 (13.29%)** | **-3.67%p** | **66** | **45** | **0.05716** |

The overall paired result does not cross the 0.05 significance threshold.

### 5.3 Pooled database results

| Database | SQL_ONLY | SQL_VALUE | Difference | SQL_ONLY-only | SQL_VALUE-only | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|
| MIMIC-IV | 75/290 (25.86%) | 39/290 (13.45%) | **-12.41%p** | 51 | 15 | **1.01×10⁻⁵** |
| eICU | 22/282 (7.80%) | 37/282 (13.12%) | **+5.32%p** | 15 | 30 | **0.03570** |

The database-specific changes point in opposite directions. Because these are
subgroup analyses and the control arm is non-contemporaneous, they are
descriptive evidence rather than confirmatory causal estimates.

### 5.4 Tool-use mechanism

| Metric | Result |
|---|---:|
| Value-search calls | 2,515 |
| SQL calls | 3,814 |
| Actual match responses | 71 |
| No-match responses | 2,443 |
| Runtime errors | 0 |
| Trajectories using value search | 310/572 |
| Trajectories with any actual match | 42/572 |
| Value-search trajectories without SQL | 85/572 |

| Outcome group | Success | SQL_VALUE-only rescue | SQL_ONLY-only regression |
|---|---:|---:|---:|
| Any actual match | 5/42 (11.9%) | 4 | 3 |
| No actual match | 71/530 (13.4%) | 41 | 63 |

Only 4 of 45 SQL_VALUE-only rescues contained an actual match. An actual match
was not associated with a higher observed task success rate. The cell-level
changes therefore cannot be attributed cleanly to successful vector
retrieval.

The operational bottlenecks were:

1. selecting a table-column pair represented in the FAISS index;
2. avoiding repeated no-match calls;
3. transitioning from retrieved values to executable SQL.

### 5.5 Cost

Saved result cost fields captured only $0.29632 and are incomplete. A prior
observed unit-cost extrapolation gives:

| Basis | Estimate |
|---|---:|
| 572 valid outcomes | Approximately $15.84 |
| 657 saved attempts | Approximately $18.20 |

These are estimates, not settled provider charges. They exclude
embedding-query costs.

## 6. Gemini 3.5 Flash matched pilot

Unlike the 2.5 Flash-Lite full comparison, both 3.5 Flash arms were executed
fresh on the same task set during the same run window.

### 6.1 Coverage and results

| Item | Result |
|---|---:|
| Logical outcomes | 48 |
| Valid outcomes | 48/48 |
| Saved attempts | 58 |
| SQL_ONLY outcomes | 24 |
| SQL_VALUE outcomes | 24 |

| Cell | SQL_ONLY | SQL_VALUE | Rescue | Regression |
|---|---:|---:|---:|---:|
| MIMIC Original | 4/6 | **6/6** | 2 | 0 |
| MIMIC Star | 4/6 | **5/6** | 1 | 0 |
| eICU Original | **3/6** | 1/6 | 0 | 2 |
| eICU Star | 3/6 | 3/6 | 1 | 1 |
| **Overall** | **14/24 (58.3%)** | **15/24 (62.5%)** | **4** | **3** |

| Paired analysis | SQL_ONLY | SQL_VALUE | Difference | Rescue | Regression | Exact p-value |
|---|---:|---:|---:|---:|---:|---:|
| Overall | 14/24 | 15/24 | +4.17%p | 4 | 3 | 1.0 |
| MIMIC pooled | 8/12 | 11/12 | +25.0%p | 3 | 0 | 0.25 |
| eICU pooled | 6/12 | 4/12 | -16.67%p | 1 | 3 | 0.625 |

The pilot is underpowered. Neither the overall nor database-pooled contrast is
statistically significant.

### 6.2 Tool-use mechanism

| Metric | Result |
|---|---:|
| Value-search calls | 32 |
| Actual match responses | 30 |
| No-match responses | 2 |
| Runtime errors | 0 |
| SQL_VALUE trajectories using value search | 22/24 |
| Search trajectories obtaining at least one match | 22/22 |
| Search trajectories without SQL | 0 |

All four rescues contained an actual match. The three regressions require
different interpretations:

- two eICU Original regressions never called value search and therefore are
  compatible with k=1 simulation or run variation rather than direct tool
  interference;
- one eICU Star regression used a successful match but did not reach a correct
  final outcome.

Direct transcript counts from
`results/value_similarity_k1_35flash_matched_available/mimic-original/sql-value/`
show that all six MIMIC Original SQL_VALUE trajectories made exactly one value
search, received a match, proceeded to SQL, and succeeded. SQL_VALUE rescued
tasks 0 and 113. On MIMIC Star, it added one rescue without a regression.

### 6.3 Observed key-usage cost

| Snapshot | `usage` | `limit_remaining` |
|---|---:|---:|
| Before pilot | 56.44161901 | 143.55838099 |
| After pilot | 63.66786216 | 136.33213784 |
| **Observed usage delta** | **$7.22624315** | |

The snapshots bracketed the pilot execution. The delta is exact for the
selected key under the assumption that no unrelated request used that key
during the interval.

## 7. Cross-model interface behavior

The two model experiments are not a controlled effect-size comparison: they
use different task scopes, baseline timing, and arm construction. Their tool
interaction traces nevertheless show a large operational contrast.

| Metric | 2.5 Flash-Lite full | 3.5 Flash matched pilot |
|---|---:|---:|
| SQL_VALUE outcomes | 572 | 24 |
| Trajectories using value search | 310 (54.2%) | 22 (91.7%) |
| Value-search calls | 2,515 | 32 |
| Actual matches | 71 (2.8% of calls) | 30 (93.8% of calls) |
| No matches | 2,443 | 2 |
| Search trajectories without SQL | 85 | 0 |
| Runtime errors | 0 | 0 |

This supports a difference in interface-use competence. It does not establish
that one model receives a larger causal benefit from retrieval.

## 8. Data-integrity and runtime incidents

### 8.1 Invalid 2.5 Flash-Lite pilot attempt

The first SQL_VALUE pilot used `text-embedding-3-small` without an available
`OPENAI_API_KEY`. All 222 value-search calls returned a missing-credentials
error. Those outcomes are excluded from every accepted result above.

A one-task smoke run confirmed that
`openrouter/openai/text-embedding-3-small` reuses the existing FAISS index and
removes the credential error. All accepted SQL_VALUE runs use that route.

### 8.2 Full-run memory exhaustion

Launching the two MIMIC FAISS-backed processes concurrently exhausted the
22 GiB host:

- MIMIC Original process RSS: approximately 10.9 GiB;
- MIMIC Star process RSS: approximately 10.7 GiB;
- kernel outcome: MIMIC Star terminated by the OOM killer.

The eICU cells remained parallel, while the MIMIC cells were serialized. The
killed process produced an empty checkpoint, which was removed. No accepted
trajectory was lost.

### 8.3 Missing-outcome repairs

| Run | Task | Cause | Repair |
|---|---:|---|---|
| 2.5 Flash-Lite full, MIMIC Original | 141 | Truncated validator JSON | Valid reward-0 outcome |
| 2.5 Flash-Lite full, MIMIC Star | 111 | Repeated simulator validation errors followed by validator JSON error | Valid reward-0 outcome |

## 9. Evidence and limits

| Evidence statement | Status |
|---|---|
| The current SQL_VALUE interface improves aggregate 2.5 Flash-Lite performance | Not supported |
| The 2.5 Flash-Lite overall change is significant at 0.05 | Not supported (`p=0.05716`) |
| The 2.5 Flash-Lite database-specific changes have the same direction | Rejected |
| Successful value retrieval explains the 2.5 Flash-Lite cell effects | Not supported |
| Gemini 3.5 Flash uses the interface more successfully than 2.5 Flash-Lite | Supported descriptively |
| The 3.5 Flash pilot establishes a positive task-success effect | Not supported (`p=1.0`) |
| The MIMIC 3.5 Flash rescue pattern warrants a larger or repeated test | Supported as a hypothesis-generating result |

Additional limitations:

- The 2.5 Flash-Lite control outcomes were generated earlier with a stochastic
  user simulator. Paired changes mix tool exposure with simulation and
  provider-time variation.
- The 3.5 Flash pilot contains only 24 pairs and seven discordant pairs.
- Cell and pooled p-values are nominal subgroup results without multiplicity
  adjustment.
- Tool output categories measure operational match/no-match behavior, not
  labeled retrieval relevance or recall.
- k=1 results do not estimate per-task success probabilities precisely.
- The 2.5 Flash-Lite provider cost is estimated rather than settled.

## 10. Conclusion

Adding the current value-similarity interface did not demonstrate an
aggregate benefit for Gemini 2.5 Flash-Lite. Its full-run result was lower
overall, with significant but opposing nominal subgroup changes: MIMIC
decreased and eICU increased. Successful retrieval was rare and did not
account for most paired outcome changes.

Gemini 3.5 Flash interacted with the same interface differently. Nearly every
value-search call returned a match, every searching trajectory proceeded to
SQL, and all four rescues contained a match. Its overall improvement was one
outcome and was not significant. The clean three-rescue, zero-regression
MIMIC pattern is hypothesis-generating rather than confirmatory.

The strongest defensible conclusion is that these runs show a descriptive
contrast in how the two models operated the table-column-parameterized
interface. A larger or repeated test should retain contemporaneous SQL_ONLY
controls and should be justified as a test of a possible model-by-tool
interaction, not as confirmation that value similarity improves end-task
accuracy.

## 11. Local raw-data locations

| Data | Path |
|---|---|
| Invalid 2.5 Flash-Lite credential-error pilot | `results/value_similarity_k1_flash_lite_pilot/` |
| OpenRouter embedding smoke | `results/value_similarity_k1_flash_lite_smoke_openrouter_embedding/` |
| Accepted 2.5 Flash-Lite value-heavy pilot | `results/value_similarity_k1_flash_lite_pilot_openrouter_embedding/` |
| 2.5 Flash-Lite full SQL_VALUE run | `results/value_similarity_k1_flash_lite_full_available_openrouter_embedding/` |
| 2.5 Flash-Lite SQL_ONLY k=1 baseline | `results/motivation_k1_flash_lite/` |
| Prior k=3 artifacts reused by the k=1 baseline | `results/increqa32_k3/` |
| 3.5 Flash fresh matched pilot | `results/value_similarity_k1_35flash_matched_available/` |
