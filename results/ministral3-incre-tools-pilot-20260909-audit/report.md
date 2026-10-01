# Ministral3 IncreQA full-vs-SQL-only pilot

All192valid outcomes complete:64permodel,32percondition, k=1.
Same16logicaltasks across Original/Star, with identical instructions andgold
answers verified acrossallmodels/conditions. Metadataallowed, benchmark
guidance anddetailedSQLerrors inbotharms. UserFlashLite temp1,nestedreflection;
validator2.5Flash n1; agenttemp0;30turns/600s,max10simulationretries.
Scoring is IncreQA SQL-result any-hit, not answer-tag scoring.

## Results

| Model | Full tool | SQL-only | Recorded pilot cost |
|---|---:|---:|---:|
| 3B | 13/32 (40.63%) | 6/32 (18.75%) | $0.4704 |
| 8B | 17/32 (53.13%) | 13/32 (40.63%) | $0.6044 |
| 14B | 18/32 (56.25%) | 16/32 (50.00%) | $0.5388 |
| 2.5 Flash-Lite historical reference | 16/32 (50%) | 6/32 (18.75%) | Separate historical run |

FlashLite uses thesame32task/schema keys butdifferent stochastic conversations
and older simulator handling. No statistical superiority claim is made.

## Full-evaluation projections

Percondition572totaloutcomes; reuse32pilot outcomes andrunonly540new.
Model/conditioncost includes saved user,agent,validator andfailed attempts.

| Model | Full total / additional | SQL-only total / additional | Full / SQL-only baseline ETA |
|---|---:|---:|---:|
| 3B | $4.28 / $4.04 | $4.13 / $3.90 | 4.7h / 5.4h |
| 8B | $4.70 / $4.44 | $6.10 / $5.76 | 6.8h / 5.9h |
| 14B | $3.86 / $3.64 | $5.77 / $5.45 | 3.1h / 4.4h |

ETA assumes4environment workers forone model/condition, cachedindices and
observed celltime pertask. It scales the slowest environment, not total
throughput alone. Treat as approximate; allowroughly25-50%margin. Both
conditions sequential needaboutthesum; simultaneous needs8workers/model.
Allthree models andbothconditions wouldrequire24workers tofinishwithin
the slowest singlecondition ETA; that schedule wasnot authorized or started.

Pilot elapsed3B29.74min,8B36.97min,14B28.21min; staggeredmodelstarts
peakedat12workers.8Bneeded one missing-only recovery for eICUSQL100 and
MIMICStarSQL94. Allother acceptedresults were retained.

## Cost and evidence

- Aggregate OpenRouter keydelta: $1.61282355 (88.652962341 -> 90.265785891).
- Toolsmokesbeforepilot: $0.00004255; all3actualget_action checks passed.
- Savedcost sum: $1.61359676; difference fromkeydelta -0.00077321.
- No unknown totalcost fields among246saved attempts. Parallelmodel billing
  preventsindependentkeydeltas; do notlabelpermodelrecordsum anaccountdelta.
-192valid,52user_error,2runtime_error; no invalidattempts assignedsynthetic0.
- All246attempts have correlatedsimulator diagnostic sidecars:9660events.
- Websearchcalls0; Tavily262->262. This doesnotguarantee zerowebcalls infullrun.
- All3native summaries complete=true with no missing/duplicates; runnerexit0
  after8Brecovery. No productioncodechanges forpilot.
- Allrun/completion/budget/memorywatchers stopped. Full evaluation notstarted.

Machine-readable analysis andpercellcheckpoint paths: `final-analysis.json`
inthisdirectory. Preflight/configs/launches retained in resultroots.
