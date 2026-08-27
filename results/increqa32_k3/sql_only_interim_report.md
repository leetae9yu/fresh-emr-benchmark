# IncreQA SQL-only
- SR: successful trajectories / trajectories
- Pass@3: tasks with at least one success in three trials
- Pass^3: tasks with three successes in three trials

## Environment cells

| Environment | Information | Feedback | Successes | SR | Pass@3 | Pass^3 |
|---|---|---:|---:|---:|---:|---:|
| eicu | available | binary | 0/48 | 0.0% | 0.0% | 0.0% |
| eicu | available | detailed | 7/48 | 14.6% | 31.2% | 6.2% |
| eicu | unavailable | binary | 0/48 | 0.0% | 0.0% | 0.0% |
| eicu | unavailable | detailed | 0/48 | 0.0% | 0.0% | 0.0% |
| eicu_star | available | binary | 0/48 | 0.0% | 0.0% | 0.0% |
| eicu_star | available | detailed | 5/48 | 10.4% | 25.0% | 0.0% |
| eicu_star | unavailable | binary | 0/48 | 0.0% | 0.0% | 0.0% |
| eicu_star | unavailable | detailed | 0/48 | 0.0% | 0.0% | 0.0% |
| mimic_iv | available | binary | 6/48 | 12.5% | 25.0% | 0.0% |
| mimic_iv | available | detailed | 18/48 | 37.5% | 75.0% | 6.2% |
| mimic_iv | unavailable | binary | 1/48 | 2.1% | 6.2% | 0.0% |
| mimic_iv | unavailable | detailed | 2/48 | 4.2% | 12.5% | 0.0% |
| mimic_iv_star | available | binary | 1/48 | 2.1% | 6.2% | 0.0% |
| mimic_iv_star | available | detailed | 11/48 | 22.9% | 43.8% | 0.0% |
| mimic_iv_star | unavailable | binary | 0/48 | 0.0% | 0.0% | 0.0% |
| mimic_iv_star | unavailable | detailed | 0/48 | 0.0% | 0.0% | 0.0% |

## Pooled SQL-only factorial cells

Each row pools the 16 MIMIC-IV and 16 eICU logical tasks.

| Schema | Information | Feedback | Successes | SR | Pass@3 | Pass^3 |
|---|---|---:|---:|---:|---:|---:|
| original | available | binary | 6/96 | 6.2% | 12.5% | 0.0% |
| original | available | detailed | 25/96 | 26.0% | 53.1% | 6.2% |
| original | unavailable | binary | 1/96 | 1.0% | 3.1% | 0.0% |
| original | unavailable | detailed | 2/96 | 2.1% | 6.2% | 0.0% |
| star | available | binary | 1/96 | 1.0% | 3.1% | 0.0% |
| star | available | detailed | 16/96 | 16.7% | 34.4% | 0.0% |
| star | unavailable | binary | 0/96 | 0.0% | 0.0% | 0.0% |
| star | unavailable | detailed | 0/96 | 0.0% | 0.0% | 0.0% |

## Logical task outcomes

Each task has 24 trials across 8 SQL-only factorial cells. `Cells` is the
number of cells with at least one success.

| Database | Task | Successes | SR | Cells |
|---|---:|---:|---:|---:|
| eicu | 2 | 1/24 | 4.2% | 1/8 |
| eicu | 16 | 0/24 | 0.0% | 0/8 |
| eicu | 21 | 1/24 | 4.2% | 1/8 |
| eicu | 33 | 0/24 | 0.0% | 0/8 |
| eicu | 34 | 1/24 | 4.2% | 1/8 |
| eicu | 42 | 0/24 | 0.0% | 0/8 |
| eicu | 43 | 1/24 | 4.2% | 1/8 |
| eicu | 49 | 0/24 | 0.0% | 0/8 |
| eicu | 54 | 0/24 | 0.0% | 0/8 |
| eicu | 84 | 0/24 | 0.0% | 0/8 |
| eicu | 85 | 0/24 | 0.0% | 0/8 |
| eicu | 89 | 0/24 | 0.0% | 0/8 |
| eicu | 108 | 4/24 | 16.7% | 2/8 |
| eicu | 111 | 2/24 | 8.3% | 1/8 |
| eicu | 114 | 2/24 | 8.3% | 2/8 |
| eicu | 134 | 0/24 | 0.0% | 0/8 |
| mimic_iv | 2 | 2/24 | 8.3% | 2/8 |
| mimic_iv | 16 | 4/24 | 16.7% | 3/8 |
| mimic_iv | 21 | 1/24 | 4.2% | 1/8 |
| mimic_iv | 33 | 1/24 | 4.2% | 1/8 |
| mimic_iv | 34 | 2/24 | 8.3% | 2/8 |
| mimic_iv | 42 | 3/24 | 12.5% | 2/8 |
| mimic_iv | 43 | 9/24 | 37.5% | 5/8 |
| mimic_iv | 49 | 5/24 | 20.8% | 3/8 |
| mimic_iv | 54 | 0/24 | 0.0% | 0/8 |
| mimic_iv | 84 | 1/24 | 4.2% | 1/8 |
| mimic_iv | 85 | 0/24 | 0.0% | 0/8 |
| mimic_iv | 89 | 0/24 | 0.0% | 0/8 |
| mimic_iv | 108 | 4/24 | 16.7% | 3/8 |
| mimic_iv | 111 | 2/24 | 8.3% | 1/8 |
| mimic_iv | 114 | 4/24 | 16.7% | 2/8 |
| mimic_iv | 134 | 1/24 | 4.2% | 1/8 |

## Interim cost and runtime

- Selected-key usage at SQL-only audit boundary: **$12.74283262**
- Provider safety-cap headroom: **$22.25716738**
- SQL-only start epoch: `1787755936`
- Audit epoch: `1787769110`
- Elapsed: **13,174 seconds (3:39:34)**

This is the requested pause boundary. The embedding-enabled half has not
started.
