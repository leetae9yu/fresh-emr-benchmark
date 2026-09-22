"""Run GPT-2 XL on both frozen matrices and print a compact artifact."""

from __future__ import annotations

import base64
import gzip
import json
import subprocess
import sys
from pathlib import Path

root = Path("/content/gpt2_probe")
jobs = (
    ("version", root / "version_eval_dataset.json"),
    ("dictionary", root / "dictionary_dataset.json"),
)
for kind, dataset in jobs:
    log = root / f"{kind}.log"
    with log.open("w") as stream:
        result = subprocess.run(
            [
                sys.executable,
                str(root / "gpt2_probe.py"),
                "--dataset",
                str(dataset),
                "--kind",
                kind,
                "--output",
                str(root / f"{kind}_scores.json"),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    if result.returncode:
        print(log.read_text()[-30000:])
        raise RuntimeError(f"{kind} probe failed")
artifact = {
    kind: json.loads((root / f"{kind}_scores.json").read_text())
    for kind, _dataset in jobs
}
payload = gzip.compress(
    json.dumps(artifact, separators=(",", ":")).encode(),
)
print("GPT2_RESULT_B64=" + base64.b64encode(payload).decode(), flush=True)
