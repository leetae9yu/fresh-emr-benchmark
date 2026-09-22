# Controlled MIMIC-III versus MIMIC-IV exposure experiment

## Conclusion

Controlled continued pretraining produced a large version-specific logit
contrast. Relative to the MIMIC-III control arm, the MIMIC-IV arm shifted
complete-identifier mean-log-probability margins by:

- **+1.9998** on IV-only probes;
- **-3.7619** on III-only probes;
- descriptive difference-in-differences: **+5.7617 nats/token**.

The corresponding complete-sequence sum-log-probability DiD is **+21.2502
nats**. Shared identifiers moved similarly in both arms (treatment-control
**+0.1532**), and eICU also moved similarly (**+0.0427**). Removing six
questionable or dependent probes leaves a positive descriptive
mean-log-probability DiD of **+4.9893**.

This supports the limited causal claim:

> Under this fixed Pythia-1B checkpoint, corpus construction, seed, and
> optimization schedule, differential MIMIC-IV versus MIMIC-III continued
> pretraining causes a version-specific identifier-preference fingerprint
> beyond the shared-schema movement seen in both arms.

It does **not** establish that the base model was naturally MIMIC-IV-clean, and
it does not justify a calibrated population-level p-value.

## Exact corpus audit

The pinned Pythia deduplicated stream was read across all **2,236 chunks** and
**600,078,336,000 bytes**. `scan_result.json` passes the exact-set coverage
gate, and zero candidate matches survived the frozen scanner's boundary
filter.

Independent review found a recall limitation: the tokenizer can merge a
preceding delimiter with the first marker characters, while the frozen scanner
searched only isolated and space-prefixed encodings. Examples such as quoted
`mimic-iv` and `mimiciv_hosp` can therefore evade the 72 compiled token
sequences. The defensible result is:

> Zero matches survived the frozen scanner's boundary filter.

The stream does contain raw frozen token sequences in non-database text (for
example `[25066, 21983]` inside “mimic ivory”), so absence of the exact token
sequences is **not** claimed. The stronger phrase “textually MIMIC-IV-clean” is
withdrawn. Consequently the base checkpoint's natural IV exposure status
remains unresolved.

## Matched intervention

- Base: `EleutherAI/pythia-1b-deduped`, pinned final commit
  `d1988145ec1cf1e76d786cd05af9f53e8b1c95cc`.
- Control: public MIMIC-III schema, documentation, and concept SQL.
- Treatment: public MIMIC-IV schema, documentation, and concept SQL.
- Source: `MIT-LCP/mimic-code` commit
  `303d26c623dcc9c49cc0f204468d4acc2f063797`.
- 83 genre- and token-length-matched document pairs.
- Exactly **2,097,152 tokens** and **512 successful optimizer updates** per
  arm.
- Same base, seed, optimizer, learning-rate schedule, sequence length, and
  update budget.
- Both histories contain updates 1..512, no retries, loss scale 128
  throughout, and finite loss/gradient/weight/logit evidence.

The packed streams contain zero boundary-valid configured opposite-version
markers. They contain 18,370 recorded III-marker occurrences in control and
16,596 IV-marker occurrences in treatment; these manipulation counts are
descriptive because the original context-wide counting method is not
occurrence-anchored.

## Frozen evaluation

The 51-item, 255-candidate matrix contains:

| Stratum | Items |
|---|---:|
| III-only | 11 |
| IV-only | 14 |
| Shared MIMIC | 10 |
| eICU | 8 |
| Generic SQL | 8 |

All candidates were scored by teacher forcing the complete identifier, with
separate prompt/target tokenization. Base, control, and treatment artifacts
each contain 255 finite rows and the same dataset digest.

### Mean-log-probability margins

| Stratum | Base | Control | Treatment | Treatment-Control |
|---|---:|---:|---:|---:|
| III-only | 1.0927 | 3.8294 | 0.0675 | -3.7619 |
| IV-only | 0.0226 | -1.2537 | 0.7460 | +1.9998 |
| Shared | 0.6646 | 4.6300 | 4.7832 | +0.1532 |
| eICU | 0.5071 | -1.5553 | -1.5126 | +0.0427 |
| Generic SQL | 1.2157 | 1.0657 | 0.1475 | -0.9182 |

The control manipulation check passes: III-only margins improve **+2.7367**
from base. The IV arm improves IV-only margins **+0.7234** from base. Both arms
improve shared MIMIC identifiers by about four nats/token.

## Statistical interpretation

The arithmetic DiD values reproduce deterministically. The originally emitted
item-bootstrap interval and item-label permutation p-value are withdrawn:
25 version probes use only 12 distinct prompts, with repeated candidates and
cross-stratum dependence, and there is one training run per arm. The result is
therefore reported as a **descriptive conditional contrast**, not calibrated
frequentist inference over independent probes or training runs.

## Limitations

1. The full-byte scan is not recall-complete for textual markers; natural IV
   exposure of the base is unresolved.
2. One IV evaluation target was misspelled (`edstay` instead of `edstays`);
   namespace prompts and two join-column prompts are also ambiguous/copyable.
   The six-item exclusion sensitivity remains positive but is post hoc.
3. The 2.1M-token streams repeat 133,303 paired tokens about 15.7 times.
4. Matching controls genre and truncated length, not clinical topic or lexical
   distribution.
5. `icd9_code` is present in the IV treatment corpus and is not a genuinely
   exclusive exposure marker.
6. Generic and shared controls use semantic prompts, whereas version probes
   use SQL-context prompts.
7. This experiment measures schema/name preference, not patient-row
   memorization, correct SQL generation, or private-record exposure.
8. Results are conditional on one model size, one seed, and one corpus pair.

## Verification

- 31 tests passed.
- Ruff: clean.
- Python no-excuse rules: clean.
- Analysis regeneration is byte-identical.
- Both training histories pass the exact matched-branch gate.
- Base/control/treatment score hashes and 255-row finite checks are recorded in
  the final gate evidence.
- Independent gate review:
  `.omo/evidence/pythia-iv-exposure-gate-review.md`.

Primary artifacts:

- `scan_result.json`
- `corpora/manifest.json`, `corpora/validation.json`
- `training/*_training_result.json`
- `version_eval_dataset.json`
- `results/{base,control,treatment}_scores.json`
- `results/analysis.json`
- `results/review_adjusted_analysis.json`
