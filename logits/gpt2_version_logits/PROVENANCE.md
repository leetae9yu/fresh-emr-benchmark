# GPT-2 XL temporal provenance

## Model

- Hugging Face repository: `openai-community/gpt2-xl`
- Scored revision:
  `15ea56dee5df4983c59b2538573817e1667135e2`
- Actual GPT-2 XL parameter count: **1,557,611,200**.
- Hugging Face safetensors metadata reports 1,607,942,848 stored float
  elements because it also counts non-parameter attention-mask buffers.

The original OpenAI GPT-2 model card states:

> Model date: February 2019, trained on data that cuts off at the end of 2017.

Source:
https://github.com/openai/gpt-2/blob/master/model_card.md

## MIMIC-IV

PhysioNet identifies the first public MIMIC-IV resource, version 0.4, as an
August 2020 release.

Source:
https://physionet.org/content/mimiciv/0.4/

## Defensible exposure statement

The original GPT-2 checkpoint's stated training cutoff precedes the public
MIMIC-IV release by more than two years. It therefore could not have trained on
the public MIMIC-IV release, its public schema documentation, or repositories
that refer to MIMIC-IV by that released identity.

This temporal argument is not a literal scan of proprietary WebText and does
not establish absence of unpublished precursor material. It also says nothing
negative about MIMIC-III: MIMIC-III was public before the WebText cutoff, and
its presence in WebText remains possible but unverified.
