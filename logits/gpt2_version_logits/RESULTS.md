# GPT-2 XL natural pre-MIMIC-IV reference

## Provenance

- Model: `openai-community/gpt2-xl`
- Immutable revision:
  `15ea56dee5df4983c59b2538573817e1667135e2`
- Parameters: 1,607,942,848
- Original OpenAI model card: February 2019 model trained on data ending
  at the end of 2017:
  https://github.com/openai/gpt-2/blob/master/model_card.md
- First public MIMIC-IV release: PhysioNet v0.4, August 2020:
  https://physionet.org/content/mimiciv/0.4/

The original GPT-2 XL checkpoint therefore cannot have received public
MIMIC-IV training data. MIMIC-III exposure remains possible but is not assumed
or proven.

## Version-specific matrix

| Stratum | Items | Mean-logprob margin | Target preference | Mean rank |
|---|---:|---:|---:|---:|
| III-only | 11 | +1.6526 | 4/11 | 2.55 |
| IV-only | 14 | -0.1519 | 2/14 | 2.93 |
| Shared | 10 | +0.5129 | 0/10 | 3.00 |
| eICU | 8 | +0.3566 | 0/8 | 2.88 |
| Generic SQL | 8 | +1.4805 | 6/8 | 1.63 |

The descriptive III-minus-IV margin is **+1.8046 nats/token**. Excluding the
same six questionable probes identified in the controlled Pythia review
increases it to **+2.3897**.

This is the expected direction for a pre-IV reference. It is compatible with
MIMIC-III-era exposure, but generic identifier age/frequency and schema
differences can also produce III preference; it is not direct corpus proof.

## Existing 655-candidate fingerprint

GPT-2's full candidate distributions are unexpectedly similar to the positive
references:

| Reference | JS similarity | Rank Spearman | Top-5 overlap |
|---|---:|---:|---:|
| OLMo | 0.8882 | 0.6168 | 0.6267 |
| Pythia | 0.9723 | 0.8144 | 0.6733 |
| Qwen | 0.9048 | 0.6682 | 0.6400 |

Yet GPT-2 places no original identifier in the top five, has mean original
rank 20.4, and prefers the star identifier by 1.7054 nats/token on average.
The strongest similarity is to Pythia, including original-minus-star margin
Spearman 0.9217.

Therefore the previously used distribution-similarity fingerprint is **not
specific to MIMIC-IV exposure**. It likely captures broad lexical, tokenizer,
prompt, and model-family preferences. The version-specific III-versus-IV
contrast is more informative than raw cross-model distribution similarity.

## Verification

- Version matrix: 255/255 finite rows.
- Dictionary matrix: 655/655 finite rows.
- Native GPT-2 tokenizer; complete-identifier teacher forcing.
- FP16 weights and logits were checked finite.
- Maximum absolute loaded weight: 5.8203125.
- Frozen dataset SHA-256 values match the local inputs.
- Raw compressed dual-matrix artifact:
  `../gpt2_remote_stdout.txt`.
