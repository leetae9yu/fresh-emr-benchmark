import json
import os
import subprocess
import sys
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from pydantic import BaseModel, JsonValue

ROOT = Path(__file__).parents[1]


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class CompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    tools: list[JsonValue] | None = None


@pytest.fixture
def local_model() -> Iterator[tuple[str, list[CompletionRequest]]]:
    requests: list[CompletionRequest] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            request = CompletionRequest.model_validate_json(body)
            requests.append(request)
            system = request.messages[0].content or ""
            if request.tools:
                if any(message.role == "tool" for message in request.messages):
                    message = {"role": "assistant", "content": "<answer>1</answer>"}
                    reason = "stop"
                else:
                    message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call_local_sql",
                            "type": "function",
                            "function": {
                                "name": "sql_execute",
                                "arguments": '{"query":"SELECT 1"}',
                            },
                        }],
                    }
                    reason = "tool_calls"
            else:
                if "determine whether [USER]" in system:
                    content = json.dumps({
                        "explanation": "Deterministic local provider.",
                        "broken_rule": "",
                        "evidence": "",
                        "result": "no_error",
                    })
                elif "supervisor of the User" in system:
                    content = "yes"
                elif len(request.messages) == 2:
                    content = "How many records are there?"
                else:
                    content = "###END###"
                message = {"role": "assistant", "content": content}
                reason = "stop"
            response = {
                "id": f"chatcmpl-local-{len(requests)}",
                "object": "chat.completion",
                "created": 1,
                "model": request.model,
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": 0.01,
                },
            }
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", requests
        finally:
            server.shutdown()
            worker.join(timeout=5)
            assert not worker.is_alive()


def test_real_runner_records_trial_and_resumes_without_requests(
    tmp_path: Path, local_model: tuple[str, list[CompletionRequest]]
) -> None:
    # Given: a real SQLite environment and a local OpenAI-compatible provider.
    endpoint, requests = local_model
    output = tmp_path / "checkpoints"
    command = [
        sys.executable, str(ROOT / "run.py"),
        "--env", "mimic_iv",
        "--task_type", "incre",
        "--model", "Qwen/Qwen3-32B",
        "--user_model", "Qwen/Qwen3-32B",
        "--validation_model", "Qwen/Qwen3-32B",
        "--api_base", endpoint,
        "--agent_strategy", "tool-calling",
        "--tool_mode", "sql_only",
        "--schema_guidance", "hidden",
        "--task_ids", "0",
        "--num_trials", "1",
        "--trial_id", "2",
        "--max_retry", "1",
        "--timeout", "30",
        "--result_dir", str(output),
    ]
    environment = {
        **os.environ,
        "OPENAI_API_KEY": "local-test-key",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # When: run the real CLI and then continue the identical trial.
    first = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60
    )
    assert first.returncode == 0, first.stdout + first.stderr
    request_count = len(requests)
    second = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60
    )
    # Then: one valid indexed trajectory; resumption does not call the provider.
    assert second.returncode == 0, second.stdout + second.stderr
    assert request_count > 0
    assert len(requests) == request_count
    latest = max(output.glob("*.jsonl"), key=lambda path: path.name)
    records = [json.loads(line) for line in latest.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["trial_id"] == 2
    assert records[0]["reward"] is not None
    assert len(records[0]["messages"]) >= 5
    assert records[0]["cost"]["total_cost"] > 0


def test_config_launcher_drives_real_runner_and_resumes(
    tmp_path: Path, local_model: tuple[str, list[CompletionRequest]]
) -> None:
    # Given: the launcher, actual run.py, SQLite, and a local model endpoint.
    endpoint, requests = local_model
    config = tmp_path / "experiment.toml"
    config.write_text(f"""
name = "local-e2e"
envs = ["mimic_iv"]
task_types = ["incre"]
trials = 2
parallel_cells = 1
result_root = "results"
[source]
path = {json.dumps(str(ROOT))}
python = {json.dumps(sys.executable)}
[defaults]
api_base = {json.dumps(endpoint)}
max_concurrency = 1
max_agent_turns = 5
max_retry = 1
timeout = 30
run_timeout = 60.0
reward_scope = "final"
[user]
model = "Qwen/Qwen3-32B"
temperature = 1.0
strategy = "nested-reflection"
[validator]
model = "Qwen/Qwen3-32B"
trials = 1
[[models]]
name = "local-model"
model = "Qwen/Qwen3-32B"
temperature = 0.0
[[conditions]]
name = "sql-only"
tool_mode = "sql_only"
schema_guidance = "hidden"
[task_ids.mimic_iv]
incre = [0]
""")
    command = [sys.executable, str(ROOT / "experiment_runner.py"), str(config)]
    environment = {
        **os.environ,
        "OPENAI_API_KEY": "local-test-key",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # When: inspect the plan, execute two indexed trials, then resume them.
    preview = subprocess.run(
        [*command, "--dry-run"], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=30,
    )
    assert preview.returncode == 0, preview.stdout + preview.stderr
    plan = json.loads(preview.stdout)
    output = Path(plan["result_dir"])
    assert not output.exists()
    assert not requests
    run = subprocess.run(
        command, cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=150,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    count_after_run = len(requests)
    resumed = subprocess.run(
        [*command, "--resume"], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=30,
    )
    # Then: no model calls on resume, separate trials and complete coverage.
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert count_after_run > 0
    assert len(requests) == count_after_run
    summary = json.loads((output / "summary.json").read_text())
    assert summary["complete"] is True
    assert summary["completed_tasks"] == 2
    manifest = json.loads((output / "manifest.json").read_text())
    assert {job["trial_id"] for job in manifest["jobs"]} == {1, 2}
    assert all(job["resumed"] for job in summary["jobs"])
    assert not list((output / "checkpoints").rglob("usage.jsonl"))
