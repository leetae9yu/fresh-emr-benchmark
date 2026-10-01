"""Run frozen Qwen Full/ATD generation jobs on a Colab T4."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import torch
from remote_infer import generate, prefix_ids
from transformers import AutoModelForCausalLM, AutoTokenizer

KIND = os.environ.get("QUICK_POC_KIND", "atd")
JOBS = Path(f"/content/quick_atd/{'dc_jobs' if KIND == 'dc' else 'jobs'}.json")
OUTPUT = Path(
    f"/content/quick_atd/{'infer_dc' if KIND == 'dc' else 'infer_qwen'}.jsonl"
)
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def main() -> None:
    raw = JOBS.read_bytes()
    jobs = json.loads(raw)["jobs"]
    OUTPUT.parent.mkdir(exist_ok=True)
    (OUTPUT.parent / f"{KIND}_jobs_sha256.txt").write_text(
        hashlib.sha256(raw).hexdigest()
    )
    done = {
        json.loads(line)["job_id"]
        for line in OUTPUT.read_text().splitlines()
    } if OUTPUT.exists() else set()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=REVISION, dtype=torch.float16, device_map={"": 0}
    )
    model.eval()
    max_weight = 0.0
    for parameter in model.parameters():
        for chunk in parameter.detach().flatten().split(65_536):
            if not torch.isfinite(chunk).all():
                raise RuntimeError("non-finite checkpoint weights")
            max_weight = max(max_weight, float(chunk.abs().max()))
    meta = {
        "model_id": MODEL_ID,
        "revision": REVISION,
        "dtype": "float16",
        "max_abs_weight": max_weight,
        "parameters_checked": sum(1 for _ in model.parameters()),
    }
    (OUTPUT.parent / f"{KIND}_model.json").write_text(json.dumps(meta, indent=2))
    print("QUICK_ATD_LOADED", flush=True)
    with OUTPUT.open("a") as stream:
        for index, job in enumerate(jobs, 1):
            if job["job_id"] in done:
                continue
            prefix = prefix_ids("qwen", tokenizer, job)
            text = generate(model, tokenizer, prefix, job["max_new_tokens"])
            stream.write(json.dumps({"job_id": job["job_id"], "text": text}) + "\n")
            stream.flush()
            print(f"QUICK_ATD_PROGRESS {index}/{len(jobs)}", flush=True)
    print("QUICK_ATD_COMPLETE", flush=True)


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
