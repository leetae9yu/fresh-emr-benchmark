# MIMIC-IV exposure experiment: final gate review

recommendation: **REJECT**

Scope: `/home/opc/kairi/emr-db-bench/EHR-ChatQA/logits/pythia_iv_exposure`, reviewed 2026-09-22. No experiment files were changed. This report is the sole review artifact written.

## originalIntent

Audit whether the completed controlled MIMIC-IV exposure experiment establishes a version-specific logit fingerprint beyond generic medical/schema learning, checking scan coverage, corpus purity and matching, training histories, scoring, statistics, controls, provenance, and limitations.

## desiredOutcome

An evidence-backed judgment about the scientific claim, not merely confirmation that output files exist or tests pass.

## userOutcomeReview

The saved scores do show a substantial version-associated contrast. The corpora reconstruct byte-for-byte from the pinned public source; the two logged training histories have equal budgets and learning-rate schedules; both published numerical analyses reproduce exactly. These are meaningful positive results.

However, the clean-base interpretation is stronger than the implemented scanner can support, and the reported confidence interval/permutation p-value do not respect the evaluation's dependence structure. Reject the claim **as presently supported and reported**, not the existence of the observed score differences. Repair the scan conclusion and statistical interpretation before treating this as a validated causal fingerprint experiment. Removing several questionable probes leaves a positive descriptive contrast; this review does not claim the effect disappears.

## Criteria and blockers

The request provided no numbered success criteria. The following IDs name criteria directly grounded in the request and policy; they are not additional architecture requirements.

### B1. HIGH: boundary-valid configured MIMIC-IV markers can evade the full-stream scanner

- violatedCriterion: **SCAN-RECALL** — the requested exact scan audit; `METHODS.md` describes explicit names/namespaces and identifier-boundary matching, and `experiment_policy.json:6` calls the base "configured-marker MIMIC-IV-clean."
- evidencePointer: `pythia_iv_exposure/scan_core.py:51-52,117-123`; `pythia_iv_exposure/source_manifest.json` (`lexical_boundary_rule`); `pythia_iv_exposure/scan_result.json` (`pattern_totals`); reproductions below.
- Observation: only isolated and space-prefixed tokenizations are searched. BPE can merge an allowed preceding delimiter with the first character of the marker. The later case-insensitive regex cannot recover a hit the byte matcher never finds.
- Direct reproduction with the pinned tokenizer and the exact 72 compiled patterns whose digest matches the SQLite run:
  - Text `'mimic-iv'`: token IDs `[1353,303,280,14,400,8]`, decoded pieces `["'m", "im", "ic", "-", "iv", "'"]`; declared boundary regex is true, scanner finds **zero hits**.
  - Text `'mimiciv_hosp'`: token IDs `[1353,303,280,400,64,73,2161,8]`; declared boundary regex is true, scanner finds **zero hits**.
  - Text `Mimic-IV`: token IDs `[46,303,280,14,3252]`; case-insensitive boundary regex is true, scanner finds **zero hits**.
- Consequence: the receipts support scanning every nominal byte for a finite set of encoded patterns, not absence of the configured textual markers. This is a demonstrated recall failure, **not proof that the actual Pile contains an IV hit**. Equal-arm continuation remains possible even if the base had prior IV exposure, but the advertised clean-to-exposed interpretation is not established.
- Required resolution: use a recall-complete strategy for the stated textual matching contract and re-establish the scan result, or explicitly narrow the conclusion to absence of the 72 exact encoded sequences and stop presenting the base as textually IV-clean.

### B2. HIGH: the published uncertainty calculation treats dependent probe contrasts as exchangeable independent observations

- violatedCriterion: **STAT-VALID** — requested validity of the DiD/bootstrap/permutation logic supporting the scientific claim.
- evidencePointer: `pythia_iv_exposure/analyze_versions.py:102-138`; `pythia_iv_exposure/version_eval_dataset.json` items `iii_only.00.mimiciii_clinical`, `iv_only.11.mimiciv_icu`, `iv_only.12.mimiciv_hosp`; `pythia_iv_exposure/results/analysis.json` (`bootstrap_ci95`, `label_permutation_p`).
- Observation: the 25 version items use only **12 distinct prompts**. The three namespace items have the identical prompt and identical candidate set, merely assigning three different answers, including answers on opposite sides of the III/IV contrast. They reuse the same five logits. Other prompt clusters contain 7, 3, 3, and 2 items with overlapping candidates. Across the full evaluation, 255 rows contain only 221 distinct `(prompt,candidate)` pairs; all repeated score values agree exactly in all three model artifacts.
- The bootstrap independently resamples 11 III and 14 IV item IDs, breaking shared-prompt/candidate and cross-stratum dependence. The permutation shuffles 25 individual arm contrasts between fixed version labels, also breaking that structure. Neither code nor methods supplies the exchangeability model that would justify this null distribution. These are not permutations of randomized training-arm assignments.
- Consequence: the arithmetic DiD is correct, but the nominal 95% interval and `p=0.00009999000099990002` cannot be presented as calibrated evidence for the causal exposure claim on this design. One training run per arm also means these are not uncertainty estimates over training runs.
- Required resolution: define the independent inferential units and a null consistent with the shared candidate/prompt design, preserving dependence in resampling/permutation; alternatively report the result as an exploratory descriptive contrast and clearly withdraw the calibrated-significance interpretation. Repeated training seeds are not imposed as a new requirement by this review.

## Additional findings, ordered by severity

### N1. MEDIUM: one "IV-only" answer is not a table, and several top-1 labels are not unique correct completions

Evidence: `version_eval_dataset.json`, item `iv_only.17.edstay`, assigns answer `edstay`. The pinned MIT-LCP archive, `mimic-iv-ed/buildmimic/postgres/create.sql:42`, defines `CREATE TABLE mimiciv_ed.edstays`. The candidate list does not contain `edstays`. The same archive's line 94 defines `mimiciv_ed.triage`.

The three namespace probes share exactly the same incomplete SQL and candidate set, yet assign different correct answers. The IV `emar` and `pharmacy` prompts likewise do not identify which valid table is intended. `top1` therefore is a target-preference summary, not task accuracy. `iii_only.09.icustay_id` and `iv_only.23.stay_id` additionally contain their answer identifier explicitly in the join prefix, allowing copying.

This is a real evaluation/reporting defect, but is not elevated to an independent invalidation of the entire fingerprint: excluding namespace items, both copyable join identifiers, and the misspelled `edstay` leaves a descriptive mean-logprob DiD of **4.989306212177983** (9 III, 10 IV items). Correct the schema spelling and label preference metrics honestly; a revised evaluation after seeing outcomes must be reported as revised rather than retrospectively preregistered.

### N2. MEDIUM: marker-boundary validation is context-wide, not anchored to the matched occurrence

Evidence: `scan_execute.py:83-93`; `scan_core.py:117-123`; `corpora/validation.json`.

`has_marker_boundaries` accepts a candidate hit if *any* bounded instance of that marker occurs within its context. With the current scanner and the actual corpus, the hit at control token 5019 is `CPTEVENTS` inside `cptevents_fk`, yet passes because a legitimate occurrence is nearby. Treatment token 9158 similarly accepts `MIMICIV` inside `mimiciv_hosp`. Thus reported "boundary_valid_hits" need not all be bounded at their recorded offsets.

Using current `context_for_hit(..., radius=96)` reproduces 18,486 accepted control hits and 16,801 treatment hits, not the artifact's 18,370 and 16,596. No validation-generator script or radius is included to account for those exact published counts. Full-decoded regex counting independently confirms **zero opposite-version forbidden markers** in both streams, so the purity conclusion survives; the manipulation counts and their wording do not have the same support.

### N3. MEDIUM: freeze chronology and trained-weight provenance remain unverified

Evidence: `experiment_policy.json:43-48`; `train_branch.py:231-247`; `score_versions.py:150-160`; `training/*_training_result.json`; `results/*_scores.json`.

The policy requires the evaluation matrix to be frozen before training. Training artifacts do not record its digest or a run-start/freeze receipt. The current dataset reproduces from its current sources, and all score artifacts use its current digest, but these checks do not establish temporal preregistration. Likewise, training artifacts name token paths but not consumed-corpus hashes; scores name remote final-model paths but not checkpoint hashes. The two final weight maxima agree between scoring and training artifacts, which is useful consistency evidence, not a checkpoint identity proof.

The local final checkpoint weights, immutable run manifest, and pretraining freeze receipt were not provided. This is an exact evidence gap, not an accusation of altered data or a demonstrated unequal-base run. It is not a separate blocker based on a newly invented requirement to ship model weights.

### N4. MEDIUM: limitations are not reported for the completed experiment

Evidence: entire `METHODS.md` (38 lines), `experiment_policy.json`, `results/analysis.json`.

The methods file documents the scan only. There is no experiment-results/limitations document in this directory. Important qualifications for the observed endpoint are:

- This is a single model size and one training seed per arm, conditional on fixed corpora and a small hand-authored probe matrix.
- The 83 paired documents contain **133,303 tokens including separators per cycle**; the 2,097,152-token stream is approximately **15.73 cycles**, not two million unique training tokens.
- Matching is exact by genre and truncated length, not by clinical topic or lexical distribution. Both arms intentionally expose the tested vocabulary; absence of verbatim evaluation prompts does not make this a held-out-vocabulary test.
- `icd9_code`, labeled III-only at evaluation, occurs **576** times in the decoded treatment stream (and 5,803 times in control). It is not an exclusive exposure marker in this public SQL corpus. IV ED/Note content is not a matched training genre under the `mimic-iv/` source prefix: `triage` and the erroneous `edstay` answer have zero occurrences in both packed streams.
- The primary DiD combines IV improvement, III improvement in control, and opposite-version loss of preference. It is not a measure of IV acquisition alone.
- Controls are not inert: shared margins improve by about 4 nats/token in each arm; eICU margins decline by about 2 in each; generic-SQL treatment-minus-control is **-0.9182**. Small shared/eICU between-arm differences do not establish statistical equivalence, and no equivalence test or tolerance is declared.
- The generic and shared controls use semantic-description prompts while version probes use SQL prefixes, so comparisons across those strata are not a matched prompt-format intervention.
- This is evidence about schema/name preferences, not private patient-row memorization, benchmark membership, or correct SQL generation.

### N5. LOW/MEDIUM: direct skill-perspective pass found ineffective coverage and weak boundaries

Loaded and consulted installed `remove-ai-slops/SKILL.md`, `programming/SKILL.md`, and `programming/references/python/README.md`. Applied the requested overfit/slop checks directly to the current source and every test module. The experiment directory is untracked, so its current full contents, not an incremental tracked patch, are the review surface.

- Excessive/useless tests: `test_training_core.py` tests `microbatch_spans`, but `train_branch.py` computes its own token slicing and never calls this helper. This is redundant production extraction and false confidence about the real training loop. The current actual slicing is correct for the frozen batch-size-one configuration.
- Requested-removal/deletion-only tests: `test_manifests.py` pins the absence of `mimic4`, `continueinnextdept`, `anchor_year`, and `poe_id` from tiers. These machine-consumed policy values are legitimate to inspect, but the exclusion pins do not test the claimed precision/recall semantics and overfit the discarded pilot cases. The scanner still misses the simple quoted positive examples above.
- Implementation-mirroring coverage: the accepted-coverage test feeds `expected_chunks()` back to the validator that uses that same function. Independent missing/unexpected-chunk tests help, and this audit separately verified the real complete set.
- Tautology/prose pins: no natural-language prose/prompt assertions or outright self-equality tests found. Dataset tests check candidate uniqueness/counts, not semantic answer validity; they pass the misspelled ED identifier.
- Core missing seams: no tests exercise the actual candidate-scoring calculation or `analyze_versions.analyze`, including DiD sign, shared-score dependence, resampling, or artifact pairing. All 31 tests can pass despite B1/B2/N1.
- Programming boundary concern: analysis consumes raw dictionaries and only checks a shared dataset-digest string and row count in `main`. It does not validate each artifact against the actual dataset or checkpoint identities. Direct inspection in this review confirms the present rows align correctly; this is not evidence the current rows are mismatched.
- Necessary versus unnecessary parsing/normalization: corpus tokenization and finite-score calculations serve the experiment. No unnecessary general-purpose production normalization subsystem was found. The unused training-span extraction is the concrete unnecessary helper.
- Existing code review report: `.omo/evidence/pythia-trajectory-code-review.md` explicitly covers the skill perspectives, but its scope is **pythia_trajectory**, not this experiment. It cannot satisfy independent code-review coverage for `pythia_iv_exposure`. No in-scope code review report, executor evidence bundle, manual QA matrix, or notepad path was supplied or located. These workflow gaps are recorded, not substituted for the direct scientific findings.

## Reproduced positive evidence

### Scan coverage and external identities

- Hugging Face API resolves `EleutherAI/pythia-1b-deduped` revision `step143000` to the policy's commit `d1988145ec1cf1e76d786cd05af9f53e8b1c95cc`.
- The pinned dataset tree contains 21 `.bin` files: twenty of 30,000,000,000 bytes and the final file of 78,336,000 bytes, totaling **600,078,336,000 bytes**.
- Opened `iv_full_scan_v3.sqlite3` read-only. `PRAGMA integrity_check` returns `ok`; the complete chunk set exactly matches the planned partition: **2,236 chunks, 600,078,336,000 nominal bytes**, no gaps/extra chunks, 2,236 distinct recorded fetched digests, empty hit tables.
- Recompiled all final patterns from the pinned tokenizer; digest is exactly `e0d6f72c2de426f3c3acb40b97b2fdd362afc159c19fc79823355f8f27053c49`, matching SQLite and JSON. Marker-manifest digest also matches.
- Inspected range validation, global shard splitting, overlap ownership, atomic receipt commit, and exact-set finalization. No coverage arithmetic bug was found.
- This session did **not** re-download/hash all 600 GB. Thus physical historical download is supported by durable receipts and code inspection, not independently replayed byte-for-byte. B1 concerns search recall, not the nominal coverage count.

### Corpora

Fetched the exact 8,128,564-byte MIT-LCP archive at commit `303d26c623dcc9c49cc0f204468d4acc2f063797`; its SHA-256 matches the corpus manifest. Re-ran collection, filtering, pairing, and stream construction in memory. The selected paths, rejection lists, matched lengths, and both final binary streams match exactly.

- 159 eligible control documents; 83 eligible treatment documents; 83 selected pairs.
- Paired genres: 60 concepts, 19 buildmimic, 4 documentation.
- Both binary streams: 2,097,152 uint16 tokens; recorded SHA-256 matches actual bytes.
- Full decoded-text, case-insensitive boundary-regex check finds zero configured opposite-version forbidden markers in either stream, independent of the flawed context-wide hit counting.
- No complete frozen evaluation prompt occurs literally in either decoded stream.

### Training and scoring

Parsed all history rows, not just first/last entries. Each arm has exactly updates 1..512, 512 one-attempt updates, loss scale 128 throughout, finite loss/gradient/LR/scale, identical learning-rate histories, and matching base commits/token budgets. Final losses: control 0.1237935838, treatment 0.0927145788. The source uses the same optimizer/schedule/seed settings for both arms. Histories are not proof of execution provenance beyond their recorded contents.

All three score files contain exactly the expected 255 unique `(item_id,candidate)` rows, with dataset-aligned answer/stratum/group fields. All aggregate scores are finite and nonpositive. Every token count matches the pinned tokenizer's encoding of the space-prefixed candidate; every mean equals sum/count. The score code uses the appropriate causal shift for separately tokenized, concatenated prompt and candidate tokens, in eval mode with complete suffix teacher forcing and FP32 scoring. It does not score raw first-token logits.

No GPU inference was rerun; checkpoint weight audits and output logits are internally consistent recorded evidence, not independently re-inferred here.

### Analysis and controls

Re-ran `analyze()` in memory for both metrics; each returned object equals the saved analysis exactly. Independently checked candidate margins and the DiD sign. The common base cancels algebraically, correctly.

| Metric | Reproduced DiD | Published item-bootstrap CI | Published label-permutation p |
|---|---:|---|---:|
| mean log probability | 5.761678334180411 | [3.9769766297523588, 7.707126546014438] | 0.00009999000099990002 |
| sum log probability | 21.250153860488496 | [13.617864727741711, 29.84881055177032] | 0.00009999000099990002 |

The resampling numbers reproduce but retain B2's inferential caveat. The add-one Monte Carlo correction and two-sided absolute-tail comparison are implemented correctly.

For the primary mean-logprob endpoint:

| Stratum | Control - base | Treatment - base | Treatment - control |
|---|---:|---:|---:|
| III-only | 2.736731 | -1.025183 | -3.761914 |
| IV-only | -1.276331 | 0.723433 | 1.999764 |
| Shared | 3.965418 | 4.118656 | 0.153238 |
| eICU | -2.062367 | -2.019656 | 0.042712 |
| Generic SQL | -0.149961 | -1.068197 | -0.918235 |

Descriptive sensitivity calculations, not substitute preregistered endpoints: removing the three namespace probes gives DiD **4.674596388737361**. The answer-only treatment-control contrast difference is **5.286683726517152**, showing the primary result is not solely deterioration of distractors. These support a real descriptive signal while not repairing B1/B2.

## Verification command and limits

Executed once:

```text
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python 3.11 --with numpy --with tokenizers --with ahocorasick-rs --with pydantic --with pytest python -m pytest -p no:cacheprovider pythia_iv_exposure -q
```

Result: **31 passed in 0.75s**. No tests were skipped, removed, edited, or retried. Additional read-only Python cells reproduced artifacts and adversarial probes as described above. They did not write experiment outputs. Lint, typecheck, build, 600-GB replay, remote training, and GPU inference were not run; no passing claim is made for them.

## Checked artifact paths

Paths below are relative to `logits/` unless external:

- `pythia_iv_exposure/METHODS.md`
- `pythia_iv_exposure/source_manifest.json`
- `pythia_iv_exposure/scan_result.json`
- `pythia_iv_exposure/marker_manifest.json`
- `pythia_iv_exposure/iv_full_scan_v3.sqlite3` (read-only SQL)
- `pythia_iv_exposure/experiment_policy.json`
- `pythia_iv_exposure/corpora/manifest.json`
- `pythia_iv_exposure/corpora/validation.json`
- `pythia_iv_exposure/corpora/control_mimiciii.uint16`
- `pythia_iv_exposure/corpora/treatment_mimiciv.uint16`
- `pythia_iv_exposure/version_eval_dataset.json`
- `pythia_iv_exposure/version_eval_controls.json` (parsed by the builder)
- `mimic_iii_iv_masked_queries.json` (parsed by the builder)
- `pythia_iv_exposure/training/control_training_result.json`
- `pythia_iv_exposure/training/treatment_training_result.json`
- `pythia_iv_exposure/results/base_scores.json`
- `pythia_iv_exposure/results/control_scores.json`
- `pythia_iv_exposure/results/treatment_scores.json`
- `pythia_iv_exposure/results/analysis.json`
- Production modules: `analyze_versions.py`, `score_versions.py`, `build_version_eval.py`, `build_corpora.py`, `corpus_core.py`, `train_branch.py`, `training_core.py`, `training_validation.py`, `constants.py`, `scan_full.py`, `scan_core.py`, `scan_execute.py`, `scan_runner.py`, `scan_store.py`, `range_reader.py`, `finalize_scan.py`, plus remote setup/status/smoke scripts, all under `pythia_iv_exposure/`.
- Every `pythia_iv_exposure/test_*.py` module (10 files).
- `.omo/evidence/pythia-trajectory-code-review.md` (verified out of scope).
- External source: `https://codeload.github.com/MIT-LCP/mimic-code/zip/303d26c623dcc9c49cc0f204468d4acc2f063797`.
- External tokenizer: `https://raw.githubusercontent.com/EleutherAI/pythia/a19eecb807ec2c79a39ebf18108816e6ffffc1d5/utils/20B_tokenizer.json`.
- External Hugging Face model revision API and pinned dataset tree API.

### Key artifact hashes at review

```text
version_eval_dataset.json              2ea5e7c4a95bbc02189c91d63b4b1d23cb66af0c40c054ac4b2b30008e148fc4
corpora/manifest.json                  c45e1d24e2ce92eca519a9d1996081aa4d69da941f64d819432d0ce036b027da
corpora/validation.json                b16fe81240db4211bcc55733577d50cb037c72cd1752651a4e77df27e394c583
training/control_training_result.json 3bdec2eeae2e74a7f40761c6676892872a86da75098a890831991b07de90f946
training/treatment_training_result.json ca9551aeaba4fbd8ab1eed66a91f2efe1570bf31321bf03b716b6071231feba8
results/base_scores.json               bc8354ae11a7e815c40669fe995ba9e13457d3f84d18d61957d345e11a578fa1
results/control_scores.json            92a20edde9162c0ccc031db0baed565b0947ef8e30e490e63f9bf9b48f7aaeca
results/treatment_scores.json          d88e2926e891e9509d5e0f9f9f75c4ddc5f77d5924ee821dac9813e289bb6e4e
results/analysis.json                  ba409c97a04a8c461dd529ee7a7779414c548b1219308b3698fa17d35f659658
```

## Exact remaining evidence gaps

1. Historical download hashes were not independently replayed against all 600,078,336,000 bytes; coverage and recorded digests were verified from SQLite and source metadata.
2. No final trained weights/checkpoint digests are present locally; no GPU rescoring or retraining was done.
3. No immutable pre-training evaluation-freeze receipt or run manifest binding dataset/corpus/code/checkpoint hashes was supplied.
4. No generator/parameters for the exact `corpora/validation.json` manipulation counts were supplied; current code plus radius 96 gives different counts.
5. No in-scope executor evidence bundle, independent code-review report with the mandated skill coverage, manual QA matrix, or notepad path was supplied or located. The only located review covers a different experiment.
6. `METHODS.md` omits training/evaluation/statistical methods and limitations of the completed experiment.

The toolkit status call returned `ULW_LOOP_PLAN_MISSING`; the requested fallback location `.omo/evidence/pythia-iv-exposure-gate-review.md` was used. No implementation fixes or commits were made.
