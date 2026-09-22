# MIMIC/eICU schema-contamination probe: cumulative results

## Executive conclusion

Exposure to MIMIC schema and identifier text can create a
version-specific logit preference. However, similarity between complete
candidate-logit distributions across models is not specific enough to diagnose
contamination by itself.

The strongest current evidence is the matched MIMIC-III versus MIMIC-IV
continued-pretraining intervention:

- MIMIC-IV treatment versus MIMIC-III control on IV-only probes: **+1.9998
  nats/token**;
- treatment versus control on III-only probes: **-3.7619 nats/token**;
- descriptive version difference-in-differences: **+5.7617 nats/token**;
- post-hoc restricted sensitivity: **+4.9893 nats/token**.

Conversely, GPT-2 XL, whose stated training cutoff predates public MIMIC-IV,
still closely matches the positive-reference candidate distributions. This
shows that the earlier cross-model fingerprint also captures generic lexical,
tokenizer, prompt, and model-family preferences.

The defensible project claim is therefore:

> Matched, version-specific within-model contrasts can reveal schema/name
> exposure effects. Raw cross-model distribution similarity cannot by itself
> establish that a naturally trained model saw MIMIC.

These experiments concern public table and column identifiers. They do not
demonstrate memorization of private patient rows.

## Experiment map

| Experiment | Exposure status | Main result | Interpretation |
|---|---|---|---|
| OLMo dictionary logits | Known positive | Reference fingerprint | Positive anchor |
| Pythia-6.9B dictionary logits | MIMIC-III hit confirmed in corpus | Strong OLMo alignment | Reproduces positive-reference structure |
| Qwen2.5-7B dictionary logits | Corpus opaque | Strongest OLMo alignment | Likely familiarity, but not verified exposure |
| Pythia early trajectory | First III hit located between step8 and step16 | Broad fingerprint growth | Specific MIMIC effect not isolated |
| Matched III/IV continued pretraining | Exposure experimentally assigned | DiD +5.7617 | Strong version-specific intervention result |
| GPT-2 XL natural reference | Training cutoff before public IV | III−IV +1.8046, but high global similarity | Version contrast useful; old global fingerprint nonspecific |

## 1. Frozen dictionary-logit matrix

The common matrix contains:

- 30 MIMIC-IV/eICU concepts;
- 655 complete-identifier candidates;
- teacher-forced sum and length-normalized mean log-probabilities;
- Original, Star, and generated distractor identifiers;
- identical candidate alignment across models.

### OLMo and Pythia

Pythia-6.9B-deduped compared with the known-positive OLMo reference:

| Metric | Result |
|---|---:|
| Jensen-Shannon similarity | 0.9144 |
| Rank Spearman | 0.7113 |
| Top-5 overlap | 0.6467 |
| Original−Star margin Spearman | 0.6383 |

Candidate-label permutation p-values were at most 0.0006. This established
that the broad fingerprint is reproducible across two model families known or
confirmed to have MIMIC-era exposure.

### Qwen2.5-7B

Qwen was even more similar to the positive references:

| Comparison | JS | Rank Spearman | Top-5 overlap |
|---|---:|---:|---:|
| Qwen–OLMo | 0.9726 | 0.8846 | 0.7867 |
| Qwen–Pythia | 0.9272 | 0.7469 | 0.6800 |

This is evidence of positive-reference-like behavior, not corpus proof:
Qwen's exact pretraining corpus is not sufficiently disclosed.

## 2. Exact Pythia early-stream trajectory

The pinned Pythia preshuffled token stream was scanned from byte zero.

First confirmed database-specific hit:

- marker: `MIMIC-III`;
- stored-token offset: **19,222,190**;
- sample: **9,381**;
- optimizer update: **10**.

The last saved pre-hit checkpoint is step8; the first saved post-hit checkpoint
is step16.

Similarity to final Pythia by checkpoint:

| Checkpoint | Rank correlation |
|---|---:|
| step0 | 0.0204 |
| step8 | 0.1300 |
| step16 | 0.2908 |
| step32 | 0.3765 |
| step64 | 0.4126 |

The preregistered step8→step16 rank increase was +0.1607 with bootstrap CI
[+0.0874, +0.2318]. However, the post-hoc difference between MIMIC and eICU
changes was only +0.0940, CI [-0.0417, +0.2393], p=0.1143.

Therefore the early jump is better explained by broad capability and lexical
learning than by an isolated MIMIC-specific event.

## 3. Controlled MIMIC-III versus MIMIC-IV exposure

Two branches were continued from the same pinned Pythia-1B checkpoint:

- control: public MIMIC-III schema, documentation, and concept SQL;
- treatment: matched public MIMIC-IV schema, documentation, and concept SQL.

Both arms used:

- 83 matched document pairs;
- exactly 2,097,152 tokens;
- exactly 512 successful optimizer updates;
- the same seed, optimizer, learning-rate schedule, and sequence length;
- finite losses, gradients, weights, and evaluation logits.

### Version-specific margins

| Stratum | Control−Base | Treatment−Base | Treatment−Control |
|---|---:|---:|---:|
| III-only | +2.7367 | -1.0252 | **-3.7619** |
| IV-only | -1.2763 | +0.7234 | **+1.9998** |
| Shared MIMIC | — | — | +0.1532 |
| eICU | — | — | +0.0427 |
| Generic SQL | — | — | -0.9182 |

The descriptive mean-logprob DiD is **+5.7617 nats/token**. Removing six
namespace, copyable, ambiguous, or erroneous probes leaves **+4.9893**.

The shared-MIMIC and eICU treatment-control differences are close to zero,
which argues against a purely generic medical/schema explanation.

### Limits

- The result has one training run per arm and is reported descriptively.
- Item-independent bootstrap and permutation inference were withdrawn because
  prompts and candidate sets are dependent.
- The original base checkpoint's natural MIMIC-IV exposure is unresolved.
- The experiment identifies schema/name preference, not patient-row recall.

Detailed report: [`pythia_iv_exposure/RESULTS.md`](pythia_iv_exposure/RESULTS.md)

## 4. GPT-2 XL natural pre-public-IV reference

The scored checkpoint is:

- `openai-community/gpt2-xl`;
- revision `15ea56dee5df4983c59b2538573817e1667135e2`;
- 1,557,611,200 parameters.

OpenAI states that GPT-2 was trained on data ending in 2017. MIMIC-IV v0.4 was
first publicly released in August 2020. The original checkpoint therefore
predates public MIMIC-IV. This temporal evidence is not a literal scan of
proprietary WebText, and MIMIC-III exposure remains possible but unverified.

### Version-specific matrix

| Stratum | Mean-logprob margin | Target preference | Mean rank |
|---|---:|---:|---:|
| III-only | +1.6526 | 4/11 | 2.55 |
| IV-only | -0.1519 | 2/14 | 2.93 |
| Shared | +0.5129 | 0/10 | 3.00 |
| eICU | +0.3566 | 0/8 | 2.88 |
| Generic SQL | +1.4805 | 6/8 | 1.63 |

The descriptive III−IV contrast is **+1.8046 nats/token**; the same six-probe
restricted sensitivity is **+2.3897**.

### Negative-control result for the old fingerprint

Despite predating public MIMIC-IV, GPT-2 strongly resembles the positive
references on the 655-candidate distributions:

| Reference | JS | Rank Spearman | Top-5 overlap | Margin Spearman |
|---|---:|---:|---:|---:|
| OLMo | 0.8882 | 0.6168 | 0.6267 | 0.5208 |
| Pythia | 0.9723 | 0.8144 | 0.6733 | 0.9217 |
| Qwen | 0.9048 | 0.6682 | 0.6400 | 0.6992 |

At the same time, GPT-2 places no Original identifier in the top five, has
mean Original rank 20.4, and prefers Star identifiers by 1.7054 nats/token on
average.

This is the decisive specificity correction: high cross-model distribution
similarity is not equivalent to MIMIC-IV exposure.

Detailed report:
[`gpt2_version_logits/RESULTS.md`](gpt2_version_logits/RESULTS.md)

## 5. Current interpretation

### Supported

1. Deliberate MIMIC version exposure changes complete-identifier logits in the
   expected version-specific direction.
2. The controlled III/IV intervention produces a large descriptive contrast
   with little corresponding movement on shared-MIMIC and eICU controls.
3. GPT-2 shows the expected III-over-IV direction for a pre-public-IV model.
4. Version-matched contrasts are more informative than global model-to-model
   fingerprint similarity.

### Not supported

1. Declaring a natural model contaminated from JS/rank/top-5 similarity alone.
2. Claiming that GPT-2 definitely trained on MIMIC-III.
3. Claiming that the Pythia base was naturally MIMIC-IV-clean.
4. Inferring patient-row or private-record memorization.
5. Treating the current one-seed descriptive DiD as calibrated
   population-level inference.

## 6. Next discriminating experiment

The next test should combine the methods from Ranaldi et al.,
arXiv:2402.08100:

1. **DC-accuracy:** mask 25% of schema identifiers after removing value clues
   and measure exact reconstruction plus complete-identifier logits.
2. **Adversarial Table Disconnection:** remove foreign-key and explicit
   relationship information, then measure the Full→ATD Text-to-SQL drop.
3. Compare GPT-2, the III-control branch, and the IV-treatment branch on
   MIMIC-III, MIMIC-IV, eICU, and a fresh/star-renamed schema.
4. Treat database/schema or query-template clusters as statistical units.

Method note:
[`literature/2402.08100.md`](literature/2402.08100.md)

## Verification summary

- OLMo/Pythia/Qwen candidate matrices: complete and finite.
- Pythia trajectory: 3,275 finite rows with pinned provenance.
- Controlled version experiment: 31 tests passed; deterministic analysis and
  matched-branch gates passed.
- GPT-2: 910 finite rows; artifact regression tests passed.
- Ruff and language-server diagnostics: clean for the GPT-2 pipeline.
- Independent final reviewers approved the controlled exposure and GPT-2
  interpretations after claim narrowing.
- OpenRouter usage: zero.

## Primary sources

- GPT-2 model card:
  https://github.com/openai/gpt-2/blob/master/model_card.md
- MIMIC-IV v0.4:
  https://physionet.org/content/mimiciv/0.4/
- Text-to-SQL contamination and ATD paper:
  https://arxiv.org/abs/2402.08100
