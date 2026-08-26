# IncreQA SQL-only trajectory analysis

This report analyzes agent behavior inside the completed SQL-only motivation
matrix. It complements `sql_only_interim_report.md`, which reports aggregate
reward metrics.

## Scope and integrity

- Branch: `report/sql-only-trajectory-analysis`
- Source experiment branch: `experiment/resumable-increqa-pilot`
- Latest immutable SQL-only signatures: **64**
- Valid trajectories: **768**
- Cells: **16 environment cells**
- Denominator: **48 trajectories per cell**
- Tasks: **16 per database**, each with three independent trials
- Superseded or interrupted rows with `reward: null` were excluded
- Binary feedback displays SQL failures as `FAILED`; detailed-only error
  categories therefore cannot be inferred in binary cells

The analysis uses the complete `messages` transcript. This is more complete
than `reward_info.pred_sql`, which omits some tool calls in max-turn
trajectories.

## Feature definitions

All features are trajectory-level and may overlap.

| Feature | Definition |
|---|---|
| Success | Outer reward equals 1 |
| Agent turn | One assistant message; tool-result messages do not add turns |
| Max-turn | Validator says the agent reached the maximum number of turns |
| Empty response | Validator records an assistant response with no content or tool call |
| SQL result | At least one `sql_execute` response was not an error or `FAILED` |
| Metadata discovery | Query references SQLite catalog tables or schema PRAGMAs |
| Blocked discovery | A metadata-discovery query occurs in an unavailable cell, where the SQLite authorizer denies it |
| Explicit missing table/column | Detailed tool output contains `no such table` or `no such column` |
| Nonexistent-table reference | SQL references a physical table absent from the target database; this does not attribute who introduced the name |
| Original-table reference | A Star trajectory references a table present only in the paired original schema |
| Distinct-name guess loop | At least three distinct missing or nonexistent table names occur in one trajectory |
| Exact-query retry | The same whitespace-normalized SQL is executed at least twice |
| Schema request | Assistant asks the user for table, column, or schema identifiers |
| Recovery to success | A rewarded trajectory had at least one earlier SQL error |

`Explicit missing table/column` is observable only with detailed feedback.
A zero in a binary cell means **masked**, not that the underlying error did
not occur.

## Executive findings

### 1. Detailed+available was associated with schema refinement and recovery

Across all environments:

| Information | Feedback | Success | Max-turn | Any SQL result | Recovery to success |
|---|---|---:|---:|---:|---:|
| available | detailed | 41/192 (21.4%) | 78/192 (40.6%) | 129/192 (67.2%) | 37/192 (19.3%) |
| available | binary | 7/192 (3.6%) | 129/192 (67.2%) | 14/192 (7.3%) | 4/192 (2.1%) |
| unavailable | detailed | 2/192 (1.0%) | 134/192 (69.8%) | 4/192 (2.1%) | 2/192 (1.0%) |
| unavailable | binary | 1/192 (0.5%) | 150/192 (78.1%) | 1/192 (0.5%) | 0/192 (0.0%) |

In available+detailed cells, **37/41 successes (90.2%)** followed an earlier
SQL error. A common observed sequence was:

1. Use a plausible table or column introduced in the conversation.
2. Receive a detailed identifier error.
3. Query `sqlite_master` or `PRAGMA table_info`.
4. Replace the guessed identifier with the discovered physical identifier.
5. Execute a rewarding query.

### 2. Binary feedback was associated with repetition rather than diagnosis

| Information | Feedback | Exact-query retry | Median SQL calls by cell |
|---|---|---:|---|
| available | detailed | 77/192 (40.1%) | 8.0-11.0 |
| available | binary | 151/192 (78.6%) | 13.0-14.5 |
| unavailable | detailed | 88/192 (45.8%) | 8.0-10.0 |
| unavailable | binary | 168/192 (87.5%) | 12.0-15.0 |

`FAILED` preserves the negative fact that execution failed, but does not
distinguish a missing table, missing column, syntax error, or blocked catalog
query. Binary trajectories frequently repeated the same SQL instead of
changing the failed identifier. This pattern is consistent with error-class
masking, but the experiment does not isolate feedback from every other
trajectory-level choice.

### 3. Unavailable+detailed conversations attempted discovery, then entered
changing-name loops

| Information | Feedback | Metadata discovery | Blocked discovery | Nonexistent-table reference | Distinct-name guess loop |
|---|---|---:|---:|---:|---:|
| available | detailed | 110/192 (57.3%) | 0/192 (0.0%) | 120/192 (62.5%) | 51/192 (26.6%) |
| available | binary | 2/192 (1.0%) | 0/192 (0.0%) | 113/192 (58.9%) | 20/192 (10.4%) |
| unavailable | detailed | 129/192 (67.2%) | 129/192 (67.2%) | 175/192 (91.1%) | 134/192 (69.8%) |
| unavailable | binary | 1/192 (0.5%) | 1/192 (0.5%) | 172/192 (89.6%) | 31/192 (16.1%) |

Detailed errors reveal that a used name is wrong, but the combined
unavailable condition provides no positive identifier through metadata or
benchmark guidance. Conversations therefore move through many plausible
names. Binary feedback preserves only generic failure, so its dominant
observed behavior is exact-query repetition rather than broad name changes.

### 4. The simulated user introduced most missing-table names in the harshest
condition

Exact-token provenance over unavailable+detailed transcripts found:

- User-first missing-table pairs: **625/926 (67.5%)**
- Missing-table trajectories with at least one user-first name:
  **142/176 (80.7%)**

| Environment | Missing-table trajectories | User-first name | Assistant-first name | User / assistant first pairs |
|---|---:|---:|---:|---:|
| `eicu` | 47 | 42/47 (89.4%) | 34/47 (72.3%) | 183 / 76 |
| `eicu_star` | 46 | 39/46 (84.8%) | 34/46 (73.9%) | 187 / 81 |
| `mimic_iv` | 37 | 25/37 (67.6%) | 31/37 (83.8%) | 99 / 59 |
| `mimic_iv_star` | 46 | 36/46 (78.3%) | 37/46 (80.4%) | 156 / 85 |

A trajectory can contain both user-first and assistant-first names. The
nested User Simulator often proposes a plausible table after a failure, and
the agent then executes SQL against it. Therefore conventional-name use cannot
be attributed solely to pretrained agent priors.

Provenance uses the first case-insensitive exact table token in user or
assistant messages, including assistant tool-call arguments. System prompt
text and tool-result echoes are excluded.

### 5. Available trajectories progressed from table errors to column errors;
unavailable trajectories remained stuck at the table stage

Detailed cells only:

| Information | Explicit missing table | Explicit missing column |
|---|---:|---:|
| available | 120/192 (62.5%) | 109/192 (56.8%) |
| unavailable | 176/192 (91.7%) | 24/192 (12.5%) |

The high column-error rate in available cells is not simply worse behavior.
It indicates that the agent often found a real table and advanced to refining
its columns. Unavailable agents usually never found a valid table.

### 6. Star success was observed only after transcript-level metadata discovery

In Star available+detailed cells:

- Metadata discovery: **65/96 (67.7%)**
- Success among discovery trajectories: **16/65 (24.6%)**
- Success without discovery: **0/31 (0.0%)**
- All **16/16 Star successes** followed both an earlier error and metadata
  discovery

In Star unavailable cells, every discovery route was blocked and success was
**0/192**.

### 7. MIMIC original cells were more successful, but attribution remains mixed

Total SQL-only success by environment:

| Environment | Success |
|---|---:|
| `mimic_iv` | 27/192 (14.1%) |
| `mimic_iv_star` | 12/192 (6.2%) |
| `eicu` | 7/192 (3.6%) |
| `eicu_star` | 5/192 (2.6%) |

The only unavailable successes were three original-MIMIC trajectories. This
is consistent with greater familiarity with MIMIC identifiers, but does not
isolate pretrained priors from task difficulty, simulator-provided names, or
other database-specific differences.

### 8. Most weak cells consumed nearly the full 30-turn budget

- The 90th percentile was **30 agent turns in every cell**.
- The median was **30 turns in 13/16 cells**. The exceptions were the three
  detailed+available cells that made the most progress:
  `mimic_iv` (19), `mimic_iv_star` (25), and `eicu` (23).
- Unavailable+binary observable means ranged from **24.74 to 27.44 turns**, consistent
  with long opaque retry loops.
- Mean turns should not be read as difficulty or causal efficiency by itself.
  Some failures end early through empty responses, while successful eICU
  recovery can require many rounds of table and column discovery.

## Per-cell outcome and conversation dynamics

`Empty/timeout` reports validator-level endings, not empty SQL result sets.

| Environment | Information | Feedback | Success | Max-turn | Empty / timeout | Median SQL calls | Any SQL result | Successful-after-error / all trials |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `eicu` | available | binary | 0/48 (0.0%) | 27/48 (56.2%) | 14/48 (29.2%) / 0 | 13.5 | 0/48 (0.0%) | 0/48 (0.0%) |
| `eicu` | available | detailed | 7/48 (14.6%) | 20/48 (41.7%) | 16/48 (33.3%) / 0 | 9.5 | 22/48 (45.8%) | 7/48 (14.6%) |
| `eicu` | unavailable | binary | 0/48 (0.0%) | 39/48 (81.2%) | 1/48 (2.1%) / 0 | 15.0 | 0/48 (0.0%) | 0/48 (0.0%) |
| `eicu` | unavailable | detailed | 0/48 (0.0%) | 37/48 (77.1%) | 1/48 (2.1%) / 1/48 (2.1%) | 10.0 | 0/48 (0.0%) | 0/48 (0.0%) |
| `eicu_star` | available | binary | 0/48 (0.0%) | 33/48 (68.8%) | 5/48 (10.4%) / 0 | 14.5 | 0/48 (0.0%) | 0/48 (0.0%) |
| `eicu_star` | available | detailed | 5/48 (10.4%) | 26/48 (54.2%) | 4/48 (8.3%) / 0 | 11.0 | 30/48 (62.5%) | 5/48 (10.4%) |
| `eicu_star` | unavailable | binary | 0/48 (0.0%) | 40/48 (83.3%) | 0 / 0 | 15.0 | 0/48 (0.0%) | 0/48 (0.0%) |
| `eicu_star` | unavailable | detailed | 0/48 (0.0%) | 37/48 (77.1%) | 1/48 (2.1%) / 0 | 10.0 | 0/48 (0.0%) | 0/48 (0.0%) |
| `mimic_iv` | available | binary | 6/48 (12.5%) | 30/48 (62.5%) | 4/48 (8.3%) / 0 | 13.0 | 11/48 (22.9%) | 3/48 (6.2%) |
| `mimic_iv` | available | detailed | 18/48 (37.5%) | 14/48 (29.2%) | 2/48 (4.2%) / 0 | 8.0 | 41/48 (85.4%) | 14/48 (29.2%) |
| `mimic_iv` | unavailable | binary | 1/48 (2.1%) | 39/48 (81.2%) | 4/48 (8.3%) / 0 | 14.0 | 1/48 (2.1%) | 0/48 (0.0%) |
| `mimic_iv` | unavailable | detailed | 2/48 (4.2%) | 30/48 (62.5%) | 7/48 (14.6%) / 0 | 8.0 | 4/48 (8.3%) | 2/48 (4.2%) |
| `mimic_iv_star` | available | binary | 1/48 (2.1%) | 39/48 (81.2%) | 1/48 (2.1%) / 0 | 14.0 | 3/48 (6.2%) | 1/48 (2.1%) |
| `mimic_iv_star` | available | detailed | 11/48 (22.9%) | 18/48 (37.5%) | 3/48 (6.2%) / 0 | 10.0 | 36/48 (75.0%) | 11/48 (22.9%) |
| `mimic_iv_star` | unavailable | binary | 0/48 (0.0%) | 32/48 (66.7%) | 3/48 (6.2%) / 1/48 (2.1%) | 12.0 | 0/48 (0.0%) | 0/48 (0.0%) |
| `mimic_iv_star` | unavailable | detailed | 0/48 (0.0%) | 30/48 (62.5%) | 2/48 (4.2%) / 0 | 9.5 | 0/48 (0.0%) | 0/48 (0.0%) |

## Per-cell agent turn distributions

An agent turn is one assistant message. A following tool-result message is
part of that turn rather than an additional turn. `Success mean` is `n/a`
when a cell has no successful trajectory. Two timeout rows had no transcript;
turn summaries exclude them and show an observed denominator of 47.

| Environment | Information | Feedback | Observed n | Mean | Median | P90 | Range | Success mean | Failure mean | Max-turn |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `eicu` | available | binary | 48 | 19.56 | 30 | 30 | 1-30 | n/a | 19.56 | 27/48 (56.2%) |
| `eicu` | available | detailed | 48 | 17.67 | 23 | 30 | 1-30 | 24.14 | 16.56 | 20/48 (41.7%) |
| `eicu` | unavailable | binary | 48 | 26.48 | 30 | 30 | 2-30 | n/a | 26.48 | 39/48 (81.2%) |
| `eicu` | unavailable | detailed | 47 | 27.13 | 30 | 30 | 9-30 | n/a | 27.13 | 37/48 (77.1%) |
| `eicu_star` | available | binary | 48 | 24.33 | 30 | 30 | 1-30 | n/a | 24.33 | 33/48 (68.8%) |
| `eicu_star` | available | detailed | 48 | 23.42 | 30 | 30 | 1-30 | 19.80 | 23.84 | 26/48 (54.2%) |
| `eicu_star` | unavailable | binary | 48 | 27.44 | 30 | 30 | 6-30 | n/a | 27.44 | 40/48 (83.3%) |
| `eicu_star` | unavailable | detailed | 48 | 26.19 | 30 | 30 | 1-30 | n/a | 26.19 | 37/48 (77.1%) |
| `mimic_iv` | available | binary | 48 | 22.67 | 30 | 30 | 2-30 | 9.33 | 24.57 | 30/48 (62.5%) |
| `mimic_iv` | available | detailed | 48 | 19.02 | 19 | 30 | 2-30 | 14.44 | 21.77 | 14/48 (29.2%) |
| `mimic_iv` | unavailable | binary | 48 | 25.46 | 30 | 30 | 2-30 | 4.00 | 25.91 | 39/48 (81.2%) |
| `mimic_iv` | unavailable | detailed | 48 | 23.25 | 30 | 30 | 1-30 | 12.00 | 23.74 | 30/48 (62.5%) |
| `mimic_iv_star` | available | binary | 48 | 26.94 | 30 | 30 | 3-30 | 21.00 | 27.06 | 39/48 (81.2%) |
| `mimic_iv_star` | available | detailed | 48 | 21.77 | 25 | 30 | 5-30 | 14.64 | 23.89 | 18/48 (37.5%) |
| `mimic_iv_star` | unavailable | binary | 47 | 24.74 | 30 | 30 | 2-30 | n/a | 24.74 | 32/48 (66.7%) |
| `mimic_iv_star` | unavailable | detailed | 48 | 24.81 | 30 | 30 | 2-30 | n/a | 24.81 | 30/48 (62.5%) |

The success/failure split is descriptive rather than causal. MIMIC and
MIMIC-Star successes were shorter than failures, while original eICU
successes averaged **24.14 turns** versus **16.56** for failures. Early empty
failures lower the latter mean, and successful eICU trajectories often contain
long discovery sequences.

## Per-cell schema behavior

`Explicit table/column` values in binary cells are masked by `FAILED`.

| Environment | Information | Feedback | Discovery | Blocked | Explicit table / column | Nonexistent reference | Original reference | Distinct loop | Exact retry | Schema request |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `eicu` | available | binary | 0 | 0 | masked | 28/48 (58.3%) | n/a | 6/48 (12.5%) | 32/48 (66.7%) | 5/48 (10.4%) |
| `eicu` | available | detailed | 21/48 (43.8%) | 0 | 29/48 (60.4%) / 13/48 (27.1%) | 29/48 (60.4%) | n/a | 15/48 (31.2%) | 19/48 (39.6%) | 28/48 (58.3%) |
| `eicu` | unavailable | binary | 1/48 (2.1%) | 1/48 (2.1%) | masked | 47/48 (97.9%) | n/a | 11/48 (22.9%) | 45/48 (93.8%) | 3/48 (6.2%) |
| `eicu` | unavailable | detailed | 35/48 (72.9%) | 35/48 (72.9%) | 47/48 (97.9%) / 1/48 (2.1%) | 47/48 (97.9%) | n/a | 40/48 (83.3%) | 24/48 (50.0%) | 46/48 (95.8%) |
| `eicu_star` | available | binary | 0 | 0 | masked | 41/48 (85.4%) | 0 | 8/48 (16.7%) | 37/48 (77.1%) | 2/48 (4.2%) |
| `eicu_star` | available | detailed | 31/48 (64.6%) | 0 | 43/48 (89.6%) / 19/48 (39.6%) | 43/48 (89.6%) | 5/48 (10.4%) | 22/48 (45.8%) | 20/48 (41.7%) | 34/48 (70.8%) |
| `eicu_star` | unavailable | binary | 0 | 0 | masked | 48/48 (100.0%) | 1/48 (2.1%) | 10/48 (20.8%) | 44/48 (91.7%) | 1/48 (2.1%) |
| `eicu_star` | unavailable | detailed | 33/48 (68.8%) | 33/48 (68.8%) | 46/48 (95.8%) / 4/48 (8.3%) | 46/48 (95.8%) | 2/48 (4.2%) | 38/48 (79.2%) | 22/48 (45.8%) | 43/48 (89.6%) |
| `mimic_iv` | available | binary | 0 | 0 | masked | 11/48 (22.9%) | n/a | 0 | 37/48 (77.1%) | 5/48 (10.4%) |
| `mimic_iv` | available | detailed | 24/48 (50.0%) | 0 | 12/48 (25.0%) / 38/48 (79.2%) | 12/48 (25.0%) | n/a | 2/48 (4.2%) | 19/48 (39.6%) | 33/48 (68.8%) |
| `mimic_iv` | unavailable | binary | 0 | 0 | masked | 33/48 (68.8%) | n/a | 2/48 (4.2%) | 41/48 (85.4%) | 3/48 (6.2%) |
| `mimic_iv` | unavailable | detailed | 28/48 (58.3%) | 28/48 (58.3%) | 37/48 (77.1%) / 18/48 (37.5%) | 36/48 (75.0%) | n/a | 20/48 (41.7%) | 19/48 (39.6%) | 41/48 (85.4%) |
| `mimic_iv_star` | available | binary | 2/48 (4.2%) | 0 | masked | 33/48 (68.8%) | 26/48 (54.2%) | 6/48 (12.5%) | 45/48 (93.8%) | 3/48 (6.2%) |
| `mimic_iv_star` | available | detailed | 34/48 (70.8%) | 0 | 36/48 (75.0%) / 39/48 (81.2%) | 36/48 (75.0%) | 29/48 (60.4%) | 12/48 (25.0%) | 19/48 (39.6%) | 44/48 (91.7%) |
| `mimic_iv_star` | unavailable | binary | 0 | 0 | masked | 44/48 (91.7%) | 22/48 (45.8%) | 8/48 (16.7%) | 38/48 (79.2%) | 2/48 (4.2%) |
| `mimic_iv_star` | unavailable | detailed | 33/48 (68.8%) | 33/48 (68.8%) | 46/48 (95.8%) / 1/48 (2.1%) | 46/48 (95.8%) | 26/48 (54.2%) | 36/48 (75.0%) | 23/48 (47.9%) | 46/48 (95.8%) |

## Cell-by-cell interpretation

### MIMIC-IV original

#### Available + detailed

- This was the most productive cell: **18/48 success** and only **14/48
  max-turn endings**.
- **14/18 successes** recovered after an SQL error; **12/18** used metadata.
- Missing-column evidence (**38/48**) greatly exceeded missing-table evidence
  (**12/48**), showing that agents usually located real MIMIC tables and then
  refined familiar but incorrect column spellings such as `patient_id`.
- Only **12/48** referenced nonexistent tables, the lowest detailed-cell rate.

#### Available + binary

- This cell still produced **6/48 successes** without normal catalog
  exploration. Familiar MIMIC identifiers are one possible explanation, but
  the design does not isolate that source.
- Exact-query retries rose to **37/48**, and max-turn endings rose to
  **30/48**.
- The contrast is consistent with schema familiarity helping some
  trajectories, while opaque failure responses are associated with less
  correction.

#### Unavailable + detailed

- Agents attempted metadata discovery in **28/48**, and every such trajectory
  was blocked.
- **37/48** encountered missing tables, **36/48** referenced a nonexistent
  table, and **20/48** cycled through at least three names.
- Two trajectories still succeeded. This is compatible with identifier
  familiarity, simulator hints, or easier tasks; the cause is not isolated.

#### Unavailable + binary

- Only **1/48** succeeded; **39/48** reached the turn limit.
- **41/48** repeated an exact SQL statement and **33/48** referenced a
  nonexistent table.
- With neither positive schema information nor identifier-level diagnostics,
  conversations mostly persisted with the current SQL rather than refining
  it.

### MIMIC-IV Star

#### Available + detailed

- **11/48 succeeded**; all 11 recovered from an earlier error and used
  metadata discovery.
- Before discovery, **29/48** referenced exact original-MIMIC tables and
  **36/48** referenced some nonexistent table.
- Common original-schema references included `admissions`, `prescriptions`,
  `patients`, `labevents`, and `icustays`.
- After discovery, transcripts switched to Star identifiers such as
  `hospitaladmissions`, `medicationorders`, and their renamed columns.

#### Available + binary

- Only **1/48** succeeded despite metadata technically being available.
- **26/48** used original-MIMIC table names, **45/48** repeated exact SQL,
  and **39/48** exhausted the turn budget.
- Catalog discovery appeared in only **2/48**. This is consistent with
  `FAILED` masking whether the problem was a table, column, or query
  structure.

#### Unavailable + detailed

- This cell had **0/48 success**.
- **33/48** attempted metadata discovery and were blocked; **46/48** then
  received missing-table errors.
- **26/48** used exact original-schema names, **46/48** used a nonexistent
  name, **36/48** entered a distinct-name loop, and **46/48** asked the user
  for schema identifiers.
- The dominant observed behavior was a sustained conventional-name sequence:
  `prescriptions` → `drug_orders` → `med_admin` →
  `medication_orders` → `pharmacy_orders`. In the representative trajectory,
  the simulated user introduced most of these names before execution.

#### Unavailable + binary

- Success remained **0/48**.
- Original-MIMIC references appeared in **22/48**, nonexistent tables in
  **44/48**, exact retries in **38/48**, and max-turn endings in **32/48**.
- Binary cells showed fewer distinct-name loops and more exact-query retries
  than detailed cells. This is an association, not an isolated causal effect.

### eICU original

#### Available + detailed

- **7/48 succeeded**; all seven recovered from an earlier identifier error.
- Metadata discovery appeared in **21/48**, while **29/48** still referenced
  nonexistent tables.
- Frequent references such as `admissions`, `prescriptions`, and `labevents`
  resemble MIMIC conventions rather than the singular eICU schema
  (`patient`, `medication`, `lab`).
- Their conversational provenance is mixed between assistant and simulated
  user, so this does not by itself establish a pretrained-prior difference.

#### Available + binary

- Success was **0/48** even though catalog access was permitted.
- Metadata discovery was never attempted; **32/48** repeated exact SQL and
  **27/48** hit max turns.
- MIMIC-like references co-occurred with no metadata discovery. Generic
  `FAILED` provided failure evidence but no identifier-level diagnosis.

#### Unavailable + detailed

- Success was **0/48**.
- **35/48** tried and were denied metadata discovery; **47/48** both referenced
  nonexistent tables and received explicit missing-table errors.
- **40/48** cycled through at least three identifiers, **46/48** asked the
  user for schema information, and **37/48** exhausted 30 turns.
- Typical names were `admissions`, `prescriptions`, `lab_results`,
  `medication_orders`, and `patient_admissions`.

#### Unavailable + binary

- Success was **0/48**, max-turn endings reached **39/48**, and exact retries
  reached **45/48**.
- One representative task repeated the same `lab_results` query six times,
  receiving only `FAILED`.
- This is the clearest pure repetition cell: the conversation receives only
  generic failure semantics and explores few alternative identifiers.

### eICU Star

#### Available + detailed

- **5/48 succeeded**; all five recovered after errors and metadata discovery.
- **43/48** referenced nonexistent tables, **31/48** used catalog/PRAGMA
  discovery, and **22/48** entered distinct-name loops.
- Exact original-eICU names were uncommon (**5/48**). Conversations more often used
  generic or MIMIC-like names such as `admissions`, `prescriptions`, and
  `diagnoses`.

#### Available + binary

- Success was **0/48**.
- Discovery was never attempted, while **41/48** used nonexistent tables,
  **37/48** repeated exact SQL, and **33/48** reached max turns.
- In this cell, metadata availability was not used when feedback did not
  identify an error class.

#### Unavailable + detailed

- Success was **0/48**.
- **33/48** attempted and were denied metadata discovery; **46/48** used a
  nonexistent table and received missing-table errors.
- **38/48** cycled through at least three names, **43/48** requested schema
  identifiers from the user, and **37/48** reached max turns.
- The dominant chain was a broad conventional-name sequence rather than use of
  exact original eICU names; user and assistant both introduced identifiers.

#### Unavailable + binary

- Success was **0/48** and every trajectory referenced at least one
  nonexistent table.
- **44/48** repeated exact SQL and **40/48** reached max turns.
- This cell combines the strongest identifier uncertainty with the least
  informative correction signal.

## Common nonexistent identifiers used in SQL

### MIMIC-IV Star

The most persistent original or conventional names used in SQL were:

- `admissions`
- `prescriptions`
- `patients`
- `labevents`
- `icustays`
- `diagnoses`
- `procedures`
- `lab_results`
- `drug_orders`

`admissions` alone was used in 20/48 available+detailed and 14/48
unavailable+detailed trajectories as a nonexistent target-table reference.

### eICU and eICU Star

The most persistent nonexistent names used in SQL were:

- `admissions`
- `prescriptions`
- `diagnoses`
- `patients`
- `procedures`
- `lab_results`
- `medications`
- `medication_orders`

These are mostly generic or MIMIC-like conventions. Exact original-eICU-only
references such as `patient`, `medication`, and `diagnosis` were comparatively
rare in Star trajectories. The provenance audit shows that many names were
introduced by the simulated user before the assistant executed them.

## Representative trajectory archetypes

### A. Original MIMIC recovery through column discovery

- Cell: `mimic_iv`, available+detailed
- Task: 2
- Sample: `9cd2abef-3185-4b69-a043-79e17a1ec7c9`
- Checkpoint:
  `mimic_iv-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_2-16-21-33_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-allowed-detailed-benchmark_embedding-text-embedding-3-small_20260826145847.jsonl`

The agent tried `patient_id`, `drugname`, and `medication`. After
`PRAGMA table_info(prescriptions)` revealed `subject_id`, `starttime`, and
`drug`, it issued the corrected query and succeeded.

### B. MIMIC Star recovery from original names

- Cell: `mimic_iv_star`, available+detailed
- Task: 2
- Sample: `90c967b6-cbdf-40b6-9a81-e7431c684c0e`
- Checkpoint:
  `mimic_iv_star-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_2-16-21-33_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-allowed-detailed-benchmark_embedding-text-embedding-3-small_20260826164426.jsonl`

The agent first used original-schema `prescriptions` and familiar column
names. `sqlite_master` exposed `medicationorders`; `PRAGMA` then exposed
`startdatetime` and `medicationname`. The corrected Star query succeeded.

### C. MIMIC Star blocked, user-assisted conventional-name loop

- Cell: `mimic_iv_star`, unavailable+detailed
- Task: 2
- Sample: `17072032-cbe3-4c29-84a7-54a982b8a5d3`
- Checkpoint:
  `mimic_iv_star-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_2-16-21-33_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-blocked-detailed-identifier_free_embedding-text-embedding-3-small_20260826165615.jsonl`

`PRAGMA table_info(prescriptions)` and `sqlite_master` were denied. The agent
then cycled through `prescriptions`, `drug_orders`,
`administered_medications`, `med_admin`, `medication_orders`,
`pharmacy_orders`, `orders`, and `drug_prescriptions`, reaching max turns.
The simulated user introduced seven of these eight names before the assistant
executed them, so this trace is a co-produced loop rather than pure autonomous
agent guessing.

### D. Original eICU recovery through table and column discovery

- Cell: `eicu`, available+detailed
- Task: 114
- Sample: `77ce9227-2cb6-445c-9a55-7d5f9fb0a6d3`
- Checkpoint:
  `eicu-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_108-111-114-134_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-allowed-detailed-benchmark_embedding-text-embedding-3-small_20260826171806.jsonl`

`procedures` and `uniquepid` failed. Catalog discovery revealed `treatment`,
and `PRAGMA table_info(treatment)` revealed `treatmentname` and
`patientunitstayid`; the corrected grouped query succeeded.

### E. Original eICU exact-query repetition under binary feedback

- Cell: `eicu`, unavailable+binary
- Task: 21
- Sample: `2b5f0f7e-a402-4f97-887d-ac0d7a077ae4`
- Checkpoint:
  `eicu-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_2-16-21-33_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-blocked-binary-identifier_free_embedding-text-embedding-3-small_20260826180328.jsonl`

The agent repeated the same `lab_results` query six times. Each call returned
only `FAILED`, so no identifier-level correction occurred.

### F. eICU Star blocked, user-assisted broad name loop

- Cell: `eicu_star`, unavailable+detailed
- Task: 54
- Sample: `76d87dc0-cf99-4748-8e96-9cb2d7a066c0`
- Checkpoint:
  `eicu_star-incre-tool-calling-gemini-2.5-flash-lite-0.0_k=3_range_54-84-85-89_user-nested-reflection-gemini-2.5-flash-lite-1.0_experiment-sql_only-blocked-detailed-identifier_free_embedding-text-embedding-3-small_20260826182100.jsonl`

After `diagnoses JOIN prescriptions` failed, two catalog queries were denied.
The agent then tried `medications`, `medication_orders`,
`drug_prescriptions`, `prescribed_medications`, `ordered_drugs`,
`medication_administration`, `prescriptions`, and `drug_orders`, then
exhausted 30 turns. The simulated user explicitly proposed these names before
their execution, so the sequence measures interaction between simulator hints
and agent SQL generation.

## Interpretation for the motivation claim

The trajectory evidence adds the following descriptive mechanism evidence to
the aggregate success-rate pattern:

1. Conversations begin with conventional or original-schema names introduced
   by both the assistant and simulated user.
2. Detailed failures expose whether the current SQL has a table- or
   column-level error.
3. When metadata is available and used, later SQL can reference discovered
   physical identifiers.
4. The combined unavailable condition is associated with blocked discovery
   and changing-name loops.
5. Binary feedback preserves generic failure but masks error class and
   identifier-level diagnostics; these cells show more exact-query repetition.

The zero-success Star+unavailable result is not evidence that SQL execution
itself was broken. Correct Star gold SQL was separately verified under blocked
metadata. The result is consistent with a floor under the combined condition
that removes both metadata discovery and identifier-bearing guidance from an
opaque renamed schema.

However, the information factor combines two interventions:

- available = metadata allowed + benchmark guidance
- unavailable = metadata blocked + identifier-free guidance

The report therefore supports the effect of the **combined information
condition**, not metadata access alone. A clean rescue experiment would hold
identifier-free guidance fixed and vary metadata access.

## Caveats

- Features overlap and should not sum to 100%.
- Identifier provenance is mixed. In unavailable+detailed cells, the simulated
  user introduced 625/926 missing-table pairs first; conventional-name use
  must not be attributed solely to autonomous agent priors.
- Binary feedback prevents post hoc classification of the underlying SQL
  error. It still communicates generic failure. Query structure and repetition
  remain observable.
- A blocked-discovery count in a binary cell is implementation-inferred from
  the query target and SQLite authorizer; `FAILED` does not expose that class
  in the transcript.
- A nonexistent-table reference may be one branch of a `UNION`; it does not
  prove every part of the query was invalid.
- Exact-query retry and distinct-name guess loop capture different failure
  modes. Binary cells favor exact repetition; unavailable+detailed cells favor
  changing-name loops.
- Agent requests for schema are detected by a fixed phrase pattern and are a
  lower bound.
- Agent turns count assistant messages. They are not token counts and do not
  count tool-result messages as separate turns.
- Two valid timeout outcomes had no transcript: eICU unavailable+detailed and
  MIMIC-Star unavailable+binary. Outcome denominators remain 48
  intention-to-treat; turn summaries use 47 observable trajectories, while
  other behavior rates are conservative count/48 incidences.
- Recovery columns use all-trial denominators. The conditional headline
  `37/41 successes` is the appropriate recovery proportion among successful
  available+detailed trajectories.
- Database/task difficulty and nested-simulator behavior are not isolated from
  schema familiarity.
- Model and simulator behavior are specific to the preregistered
  `gemini-2.5-flash-lite` setup and 30-turn limit.
- Three trials per task support descriptive mechanism analysis but not precise
  per-task behavioral probabilities.
