# /// script
# requires-python = ">=3.11"
# dependencies = ["torch>=2.4", "transformers==4.48.3"]
# ///
"""Score frozen MIMIC matrices with pinned GPT-2 XL."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing_extensions import override

MODEL_ID: Final = "openai-community/gpt2-xl"
MODEL_REVISION: Final = "15ea56dee5df4983c59b2538573817e1667135e2"


@dataclass(frozen=True, slots=True)
class ProbeError(RuntimeError):
    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


@torch.inference_mode()
def score_candidate(model, tokenizer, prompt: str, candidate: str) -> dict:
    prefix_ids = tokenizer.encode(prompt, add_special_tokens=False)
    suffix = " " + candidate
    suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
    if tokenizer.decode(
        suffix_ids,
        clean_up_tokenization_spaces=False,
    ) != suffix:
        raise ProbeError("Candidate does not round-trip through tokenizer")
    ids = prefix_ids + suffix_ids
    start = len(prefix_ids)
    inputs = torch.tensor([ids[:-1]], dtype=torch.long, device="cuda")
    logits = model(input_ids=inputs, use_cache=False).logits
    if not torch.isfinite(logits).all():
        raise ProbeError("Non-finite GPT-2 logits")
    target_logits = logits[0, start - 1:].float()
    targets = torch.tensor(suffix_ids, device="cuda")
    selected = target_logits.gather(1, targets[:, None]).squeeze(1)
    logprobs = selected - torch.logsumexp(target_logits, dim=-1)
    total = float(logprobs.sum().item())
    return {
        "candidate": candidate,
        "sum_logprob": total,
        "mean_logprob": total / len(suffix_ids),
        "token_count": len(suffix_ids),
    }


def version_items(raw: dict) -> list[dict]:
    return raw["items"]


def dictionary_items(raw: dict) -> list[dict]:
    return [
        {
            "item_id": item["item_id"],
            "stratum": item["database"],
            "group": item["kind"],
            "answer": item["original"],
            "prompt": item["prompt"],
            "candidates": [
                candidate["value"]
                for candidate in item["candidates"]
            ],
        }
        for item in raw["items"]
    ]


def run(dataset_path: Path, kind: str, output_path: Path) -> None:
    if not torch.cuda.is_available():
        raise ProbeError("CUDA is required")
    raw_bytes = dataset_path.read_bytes()
    raw = json.loads(raw_bytes)
    items = version_items(raw) if kind == "version" else dictionary_items(raw)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    ).cuda().eval()
    max_weight = 0.0
    for parameter in model.parameters():
        if not torch.isfinite(parameter).all():
            raise ProbeError("Non-finite GPT-2 weights")
        max_weight = max(max_weight, float(parameter.abs().max().item()))
    rows = []
    for index, item in enumerate(items, start=1):
        for candidate in item["candidates"]:
            rows.append({
                "item_id": item["item_id"],
                "stratum": item["stratum"],
                "group": item["group"],
                "answer": item["answer"],
                **score_candidate(
                    model,
                    tokenizer,
                    item["prompt"],
                    candidate,
                ),
            })
        print(f"GPT2_PROGRESS {kind} {index}/{len(items)}", flush=True)
    output_path.write_text(json.dumps({
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "webtext_cutoff": "end of 2017",
        "dataset_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "dtype": "torch.float16",
        "max_abs_weight": max_weight,
        "rows": rows,
    }, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dataset", type=Path, required=True)
    _ = parser.add_argument(
        "--kind",
        choices=("version", "dictionary"),
        required=True,
    )
    _ = parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.dataset, arguments.kind, arguments.output)


if __name__ == "__main__":
    main()
