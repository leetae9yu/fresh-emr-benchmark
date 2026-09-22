"""Persist complete GPT-2 remote stdout before the Colab session is reclaimed."""

from __future__ import annotations

import subprocess
from pathlib import Path

root = Path(__file__).parent
result = subprocess.run(
    [
        "/home/opc/.local/bin/colab",
        "exec",
        "-s",
        "gpt2-probe",
        "-f",
        str(root / "gpt2_remote.py"),
        "--timeout",
        "7200",
    ],
    text=True,
    capture_output=True,
    check=False,
)
_ = (root / "gpt2_remote_stdout.txt").write_text(result.stdout)
_ = (root / "gpt2_remote_stderr.txt").write_text(result.stderr)
print(result.returncode, len(result.stdout), len(result.stderr))
if result.returncode:
    raise RuntimeError("GPT-2 remote run failed")
