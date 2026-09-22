# GPT-2 XL natural pre-MIMIC-IV reference: final gate

- recommendation: **APPROVE**
- blockers: []
- Review date: 2026-09-22
- Scope: completed experiment and its scientific claims, not a general production-readiness gate.
- No HIGH failure of the requested success criteria was found. Medium limitations are below.

## originalIntent

As stated in the gate task, establish whether the completed GPT-2 XL experiment supplies a defensible natural pre-public-MIMIC-IV reference, with correct frozen-matrix scores and reproducible descriptive comparisons. Do not infer training membership or a causal exposure effect from identifier preference alone. A separate original user brief was not supplied; this interpretation uses the explicit task, not inferred executor promises.

## desiredOutcome

A reader can trust the reported III-versus-IV arithmetic and dictionary comparisons, distinguish chronological exclusion of public MIMIC-IV from unknown MIMIC-III exposure, and understand that high cross-model similarity is not specific evidence of MIMIC-IV exposure.

## userOutcomeReview

The artifact meets that outcome. Independently decoding the raw payload and recomputing the metrics reproduces both analysis files. Chronological exclusion is supported by primary sources. The report explicitly treats MIMIC-III exposure as possible, calls the version contrast descriptive, and does not present a significance test or causal estimate. Its proposed lexical/tokenizer explanation remains a hypothesis, not a demonstrated mechanism. Approval does not certify every metadata detail or every engineering quality gate as clean.

## Criteria and direct checks

The IDs below label the success criteria stated in the task; they are not additional requirements.

| Criterion | Result | Evidence |
|---|---|---|
| ROW-SCORE: frozen row/score integrity | PASS for stored scores | Raw dual payload, frozen datasets, pinned tokenizer, reference score files |
| PRE-IV: defensible exclusion of public MIMIC-IV | PASS | Original OpenAI model card; PhysioNet MIMIC-IV v0.4 page; pinned HF revision |
| III-UNCERTAINTY: possible, not proven III exposure | PASS | RESULTS.md provenance and version interpretation; analysis interpretation |
| VERSION-ARITH: reproducible III-minus-IV descriptive contrast | PASS | Independent recomputation from 255 raw rows |
| SIMILARITY-ARITH: reproducible 655-candidate interpretation | PASS | Independent SciPy recomputation from raw GPT-2 and reference scores |
| CLAIM-SCOPE: no exposure/causality overclaim | PASS, with limitations | Explicit descriptive and possible-exposure caveats; no causal or calibrated inferential claim |

### Row and scoring integrity

Decoded exactly one `GPT2_RESULT_B64=` payload using strict base64 decoding and gzip. Its file SHA-256 is `e5f214618586ef36245ce64754ca83032acd1eb4223258340260107de0a1d97d`, matching both analysis files.

- Version: 51 items, 255 unique exact `(item_id, candidate)` rows.
- Dictionary: 30 items, 655 unique exact `(item_id, candidate)` rows.
- Checked complete expected key sets, no duplicates/extras, candidate identity, stratum/group/answer metadata, finite negative scores, positive token counts, and `sum_logprob / token_count == mean_logprob` to numerical tolerance.
- Version dataset SHA-256: `2ea5e7c4a95bbc02189c91d63b4b1d23cb66af0c40c054ac4b2b30008e148fc4`.
- Dictionary dataset SHA-256: `00e216c96ca4142b7bdc30a5114a2b340df9d8a0a4f72060b128658aac221125`. This is the Pythia dictionary dataset; its items are identical to OLMo's and Qwen's despite differing model metadata.
- Verified version source hashes and reconstructed all 51 items from the source queries and controls. Rebuilt the frozen OLMo matrix from `biomistral_dictionary/candidates.json` in memory and compared its full typed value with the frozen dataset.
- Downloaded the pinned tokenizer JSON into memory. SHA-256: `8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6`.
- All 910 suffixes round-trip as exactly one leading space plus the candidate; all recorded token counts match. Separate prefix/suffix tokenization agrees with concatenated-string tokenization for every scored pair.
- Maximum complete sequence lengths are 103 tokens (version) and 231 (dictionary), below the pinned model's 1,024-token context.
- Repeated identical prompt/candidate pairs have exactly equal scores.
- Inspected `gpt2_probe.py:33-59`: inputs omit the final token; logits start at prefix length minus one; targets are all suffix tokens. This is correctly shifted complete-identifier teacher forcing, with FP32 log-normalization of FP16 model logits.
- Inspected finite-weight/logit checks and remote failure propagation. The remote payload is emitted only after both subprocesses succeed. The payload records maximum absolute weight 5.8203125 for both jobs.

Reference artifacts were also checked against their own dataset hashes and complete exact candidate sets. All per-token values are finite; sums and means reproduce. An initial overly strict double-precision subtraction check failed on four reference tokens. Investigation showed these are exactly FP32 subtraction roundoff, maximum `9.5367431640625e-07`; explicit NumPy FP32 subtraction reproduces every stored token log-probability. This is not a score-integrity defect.

Reference score SHA-256 values:

- OLMo: `ffd6251fd2de61a425f8a3571697a7544508fb12c486a678c62c6389724bf2f3`
- Pythia: `883936fb86ea6024446a807f252f85b9a1e4a01055773bfbd7209a028fdd451a`
- Qwen: `7b5e7b9490c2fe26ebfecd1306ae1340f2f3cb005f0b246aca80457f356704d8`

### Version arithmetic

Independently calculated each item's target mean-logprob minus the arithmetic mean of its four distractors. Rank is one plus the number of strictly higher candidate scores. Target preference means rank one, not merely positive margin.

| Stratum | Items | Recomputed mean margin | Target top-one | Mean rank |
|---|---:|---:|---:|---:|
| III-only | 11 | 1.6526495546489566 | 4/11 | 2.5454545454545454 |
| IV-only | 14 | -0.15190769085267758 | 2/14 | 2.9285714285714284 |
| Shared | 10 | 0.5129401775201161 | 0/10 | 3.0 |
| eICU | 8 | 0.35657848666111625 | 0/8 | 2.875 |
| Generic SQL | 8 | 1.4805391430854797 | 6/8 | 1.625 |

III-minus-IV: **1.804557245501634** nats/token.

The excluded IDs exactly match `pythia_iv_exposure/results/review_adjusted_analysis.json`: three namespace items, two join-column items, and the `edstay` item. Remaining means are III `1.9491057638138058` (9 items), IV `-0.4406257469313484` (10 items), contrast **2.3897315107451544**. This is sensitivity analysis, not a new independent experiment.

### Dictionary arithmetic

Used SciPy `softmax`, `jensenshannon(..., base=2)`, and `spearmanr`, independently of the repository comparison helpers. JS similarity is `1 - JS divergence/log(2)`, equivalently one minus squared base-2 Jensen-Shannon distance. Metrics are averaged equally over the 30 concepts, not over one pooled 655-dimensional distribution. Top-five overlap is shared members divided by five.

| Reference | JS similarity | Rank Spearman | Top-five overlap | Original-star margin Spearman |
|---|---:|---:|---:|---:|
| OLMo | 0.888175651370718 | 0.616825895389953 | 0.6266666666666667 | 0.5208008898776418 |
| Pythia | 0.9723495655247718 | 0.8143827962248511 | 0.6733333333333333 | 0.921690767519466 |
| Qwen | 0.9048168749413745 | 0.6682443970051951 | 0.64 | 0.6992213570634038 |

All match the published JSON within `1e-12`. Original top-five count is 0/30, mean rank 20.4, observed rank range 8-22. Original-minus-star mean margins reproduce as all `-1.7054287513854012`, MIMIC-IV `-0.780432236081078`, eICU `-2.6304252666897243`.

These results substantiate a counterexample to interpreting high similarity alone as IV-exposure evidence. They do not establish that all similarity-based methods fail, identify the causal mechanism, prove MIMIC-III membership, or establish a calibrated detector's sensitivity/specificity.

### Provenance reproduced from primary sources

Consulted live on 2026-09-22:

1. https://raw.githubusercontent.com/openai/gpt-2/master/model_card.md
   - Explicitly says: "February 2019, trained on data that cuts off at the end of 2017."
   - Describes the largest/fourth GPT-2 version and was last updated November 2019.
   - Retrieved content SHA-256: `b89feaa5629a565a6451ab7e101f85af334531590b6a55ec832123100286c05c`.
2. https://physionet.org/content/mimiciv/0.4/
   - Displays "Published: Aug. 13, 2020. Version: 0.4" and the 2020 citation.
3. https://huggingface.co/api/models/openai-community/gpt2-xl/revision/15ea56dee5df4983c59b2538573817e1667135e2
   - Resolves the exact pinned commit and GPT2LMHeadModel configuration.
4. https://huggingface.co/openai-community/gpt2-xl/raw/15ea56dee5df4983c59b2538573817e1667135e2/README.md
   - Identifies the released OpenAI pretrained XL model, not a later MIMIC fine-tune.
5. https://physionet.org/content/mimiciii/1.4/
   - Displays September 4, 2016 publication: compatible with possible III-era exposure, not evidence of WebText membership.

The timeline defensibly excludes the later public IV release. Even distinguishing historical Reddit-link selection dates from possible subsequent page changes does not overturn the original model's 2019 existence before the cited 2020 release. The claim must remain about public release exposure, not absence of shared earlier identifiers, overlapping medical concepts, or private precursor material.

## Medium limitations and factual correction

1. **Parameter metadata correction.** `gpt2_version_logits/RESULTS.md:10` labels 1,607,942,848 as parameters. The pinned safetensors header contains that many stored elements, including 48 non-parameter causal-mask buffers of shape 1 x 1 x 1024 x 1024. Trainable/tied-model parameter count is **1,557,611,200**. Independently derived this from the pinned config and confirmed the tensor-header count using an HTTP range request to `https://huggingface.co/openai-community/gpt2-xl/resolve/15ea56dee5df4983c59b2538573817e1667135e2/model.safetensors`. This does not change model identity, chronology, scores, or the requested comparisons.
2. **Measurement limitations.** There are only 12 distinct prompts among 25 version items; namespace ambiguity, copyable join columns, misspelled `edstay`, shared legacy identifiers, and different prompt genres limit interpretation. Candidate distributions use per-model token-normalized scores; lexical length and tokenizer preferences can drive similarity. The report's "more informative" version-contrast sentence is a qualitative suggestion, not validated detector superiority. The causal lexical/tokenizer explanation remains untested. Descriptive wording prevents these from becoming HIGH inferential failures.
3. **Audit/reproduction limitations.** No GPT-2 analysis-generation script, experiment-specific regression tests, dedicated code-review report, manual QA matrix, notepad path, or original standalone brief was supplied/found in the scoped artifact/evidence locations. Primary sources are named in RESULTS.md but not linked there. This gate supplies direct checks and source URLs, not a claim that those absent artifacts exist.
4. **Engineering quality is not clean.** LSP diagnostics on `gpt2_probe.py` report five missing-generic-type-argument errors at lines 34, 62, 66, plus a Transformers `.cuda()` self-argument diagnostic at line 93 and unknown/Any warnings. `gpt2_remote.py` has no diagnostics. Raw dictionary boundaries, untyped scorer collaborators, and lack of GPT-2 regression coverage create maintenance burden. These are not demonstrated failures of this completed scientific artifact's stated success criteria.

## Direct remove-ai-slops / programming review

Loaded both installed skills and the Python reference. Applied their criteria directly without implementing changes.

- Diff availability: the whole logits directory is untracked relative to the enclosing repository; no meaningful tracked before/after GPT-2 diff was supplied. Reviewed the complete in-scope source files as new additions instead.
- Excessive/useless tests: no GPT-2-specific tests exist. Existing comparison tests are small and relevant but cannot prove this experiment's full integrity.
- Deletion-only/removal-verification tests: none in the inspected test files.
- Tautological tests: none found. Identity-distribution tests assert known mathematical identities from inputs, not values re-derived from the implementation's output. They are narrow coverage, not complete coverage.
- Implementation-mirroring/prose-pinning tests: none found in the inspected comparison tests. This gate's numerical check uses independent SciPy primitives and actual frozen inputs.
- Unnecessary extraction: `version_items` is a pass-through wrapper (`gpt2_probe.py:62-63`); minor maintenance note only.
- Parsing/normalization: JSON plus gzip/base64 transport has a concrete purpose; no speculative parser or normalization layer. Token round-trip and finite checks are legitimate numerical/system-boundary checks.
- Error handling: finite failures raise; remote subprocess failure prints the job log and raises. No swallowed exceptions or broad catches in the in-scope code.
- Complexity/scope: source modules contain 122 and 43 nonblank/noncomment lines, respectively. No oversized module, speculative framework, unrelated refactor, or scope drift found.
- Programming gaps: raw dict signatures and JSON objects flow without typed parsing; kind dispatch is a non-exhaustive string branch; scorer collaborators are untyped; no demonstrated TDD/GPT-2-specific regression coverage. Recorded as engineering limitations, not hidden by artifact success.
- A dedicated GPT-2 code-review report is absent, so its explicit coverage of these perspectives **cannot be confirmed**. This is an exact evidence gap, not a substitute for this direct review and not an invented HIGH research blocker.

## Verification execution and exact evidence gaps

- In-memory Python checks reproduced raw decoding, dataset alignment, tokenizer behavior, score arithmetic, source reconstruction, all reported metrics, and reference token aggregation.
- Syntax compilation of both GPT-2 source files succeeded without writing bytecode.
- Ran once:
  `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 --with pytest --with pydantic --with typing-extensions python -m pytest -p no:cacheprovider pythia_dictionary_logits/test_compare.py qwen_dictionary_logits/test_compare.py -q`
  Result: **6 passed in 0.12s**. These are related metric tests, not a GPT-2 inference rerun.
- CUDA is unavailable on this workstation. Full model inference, actual loaded-weight finiteness, and all original logits were **not independently rerun**. The payload lacks per-token GPT-2 logits and environment/library-version provenance; source checks and aggregate scores do not reconstruct those missing records.
- Initial offline tokenizer loading failed because the pinned tokenizer was not locally cached. Resolved by fetching its immutable tokenizer JSON directly into memory; all tokenizer checks then passed.
- Initial reference subtraction failure was investigated and resolved as FP32 rounding, as detailed above; no failing check was suppressed.
- No experiment files were edited and no fixes were implemented. Build: not applicable to this review-only Python experiment. LSP is explicitly not clean; no clean typecheck claim is made.

## Checked artifact paths

Read or machine-inspected:

- `gpt2_probe.py`, `gpt2_remote.py`, `gpt2_run_local.py`, `gpt2_setup.py`
- `gpt2_remote_stdout.txt`, `gpt2_remote_stderr.txt`
- `gpt2_version_logits/analysis.json`, `gpt2_version_logits/RESULTS.md`
- `gpt2_dictionary_logits/analysis.json`
- `mimic_iii_iv_masked_queries.json`
- `pythia_iv_exposure/version_eval_dataset.json`, `version_eval_controls.json`, `build_version_eval.py`, `analyze_versions.py`, `RESULTS.md`, `results/review_adjusted_analysis.json`
- `biomistral_dictionary/candidates.json`
- `olmo_dictionary_logits/dataset.json`, `scores.json`, `build_dataset.py`, `analyze.py`
- `pythia_dictionary_logits/dataset.json`, `scores.json`, `source_manifest.json`, `build_dataset.py`, `compare.py`, `comparison_build.py`, `test_compare.py`
- `qwen_dictionary_logits/dataset.json`, `scores.json`, `test_compare.py`
- `.omo/evidence/` and `.senpi/` artifact listings/searches for GPT-2 review/notepad evidence
- Installed skills: `/home/opc/.local/lib/node_modules/omo-ai/plugin/skills/{remove-ai-slops,programming}/SKILL.md` and `programming/references/python/README.md`
- Primary-source URLs listed above and the pinned `config.json`/`tokenizer.json`/safetensors header.

Reviewed GPT-2 content hashes:

| File | SHA-256 |
|---|---|
| gpt2_probe.py | 9599f7d2b8076784e9566939fc27f357921ea61f30525b7d74a0ec6974f71a84 |
| gpt2_remote.py | 460a0154505cff1088106bdbd4ef95567fe2634524ff898f39f5976c784cc4d1 |
| RESULTS.md | 4fbe788e10d3b643e66372cc27fd44a4fa2a75bbe7a2c72b830261ecc6a4f325 |
| Version analysis | 0b923ba30c92dc78ff28b99c52809043cddc404c33150265316d60278c26d7a6 |
| Dictionary analysis | d587e92ff504bb457a9d7fd6c9dc32518ca22a0cdfcadd143614b4924006c94e |

## Report placement

Consulted the requested toolkit status via a Bun JavaScript eval with `agentToolkit.status()`. It returned `ULW_LOOP_PLAN_MISSING` and no `currentAttemptDir`; used fallback `.omo/evidence/gpt2-probe-gate-review.md`. This report is the only intentional repository artifact written by the gate reviewer.
