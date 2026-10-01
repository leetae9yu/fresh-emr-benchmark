# Flash-Lite full-tool IncreQA full evaluation

Completed 2026-09-09T08:40:51.589Z: **572/572 valid outcomes, 324 successes (56.64%)**.

| Environment | Successes / valid | Rate |
|---|---:|---:|
| mimic_iv | 78/145 | 53.79% |
| mimic_iv_star | 91/145 | 62.76% |
| eicu | 69/141 | 48.94% |
| eicu_star | 86/141 | 60.99% |

## Conditions

Gemini 2.5 Flash-Lite agent at temperature0; six tools; metadata allowed;
benchmark guidance; detailed SQL errors; k=1. User Flash-Lite temperature1,
nested reflection; validator Gemini2.5Flash n=1. Per-task600seconds/30turns,
max_retry10. **IncreQA uses SQL-result any-hit scoring, not answer tags.**

All32pilot valid outcomes (16successes/16failures) were reused, with all68
pilot attempt payloads unchanged. The remaining540 valid outcomes used
the repaired simulator source recorded in analysis.json. Pilot and new
source versions differ; do not describe the cohort as unchanged-code.

The user approved serial ->3 ->4environment concurrency; one worker per
environment throughout. All saved outcomes were seeded verbatim between
separate result roots. The initial full pass reached568/572; one same-config
missing-only recovery completed MIMICOriginal75,99,103 andeICUOriginal132.
No model, task limit, scoring or prompt changes were made during execution.

## Preservation and failures

Verified unchanged hashes for29pilot files,67serial-run files and147
three-parallel files. All68pilot payloads match the final checkpoints.
There are768distinct attempts:572valid,176user_error and20runtime_error.
Valid score0 outcomes comprise55nonterminal conversations and193terminated
SQL-result mismatches. These are not classified as missing-answer-tag errors.

All700new checkpointed attempts have linked diagnostics, totaling40613
events across retained result roots. Two additional partial diagnostic
sidecars from transitions are preserved even though their interrupted
attempts did not produce a checkpoint outcome. Failed attempts are not
scored as zero merely to fill coverage.

## Cost and time

- New OpenRouter cost: **$6.070903**, usage82.156023071 ->88.226926071.
- Already-paid pilot: $0.52050398.
- **Total including pilot: $6.59140698.**
- Tavily:11advanced searches,22credits; reported240 ->262, reconciled.
- Started2026-09-09T04:40:14.183Z; ended2026-09-09T08:40:51.589Z.
- Elapsed including transitions/recovery: **4h00m37.406s**.

Native launcher completed with exit0, complete=true and no missing/duplicate
slots. Previous source inventories and pilot payloads passed hash checks.
All run/completion/budget/memory watches are stopped. No production code
was changed for this evaluation; prior simulator tests remain its code
verification evidence, not a newly claimed full-suite pass.

## Artifacts

Final config: experiments/gemini25fl-full-incre-eval-parallel4.toml.
Result root: results/config-runner/gemini25fl-full-incre-eval-parallel4-20260909-6320140c1025cfaea373c3820c36ea253b43e39038cc5e21da48a5e6e4c3fe6d.
It contains summary.json, analysis.json, logs/checkpoints, diagnostic links
and parallel_transition.json. Earlier roots are preserved and indexed in
analysis.json.
