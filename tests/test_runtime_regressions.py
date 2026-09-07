import json
import sqlite3
import sys
from argparse import Namespace
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine

import run as runner
import src.utils as utils
import validator
from src.agents.base import AgentTimeoutError
from src.agents.tool_calling_agent import ToolCallingAgent
from src.envs.base import Env
from src.envs.eicu_star.tools.sql_execute import SQLExecute
from src.envs.user import LLMUser
from src.types import CostInfo, EnvInfo, EnvRunResult, RewardInfo, Task, ValidationResult


def config(tmp_path, **overrides):
    values = dict(env="mimic_iv_star", task_type="incre", model="openrouter/google/gemini-2.5-flash",
                  user_model="gemini/gemini-2.5-flash", agent_strategy="tool-calling", temperature=0.0,
                  user_strategy="nested-reflection", user_temperature=1.0, num_trials=1,
                  task_ids=[0], start_index=0, end_index=-1, result_dir=str(tmp_path), api_base=None,
                  embedding_model="text-embedding-3-large", validation_model="gemini/gemini-2.5-flash",
                  validation_trials=1, max_agent_turns=3, max_retry=1, timeout=20, max_concurrency=1,
                  verbose=False)
    values.update(overrides)
    return Namespace(**values)


def task():
    return Task(db_id="mimic_iv_star", task_type="incre", task_id="0", instruction="Count rows",
                gold_sql="SELECT 1", gold_answer=[[1]])


def row(sample="sample", **overrides):
    values = dict(db_id="mimic_iv_star", task_type="incre", task_id="0", sample_id=sample,
                  trial_id=1, reward=1.0, info=EnvInfo(task=task(), reward_info=RewardInfo()),
                  messages=[{"role": "user", "content": "Count rows"}],
                  cost=CostInfo(agent_cost=0.1, user_cost=0.2, eval_cost=0.3, total_cost=0.6))
    values.update(overrides)
    return EnvRunResult.model_validate(values)


def response(content: str | None = "answer", cost: float | None = 0.25, tool=False):
    message: dict[str, Any] = {"role": "assistant", "content": content, "tool_calls": None}
    if tool:
        message["tool_calls"] = [{"id": "sql-1", "type": "function", "function": {
            "name": "sql_execute", "arguments": '{"query":"SELECT 1"}'}}]
    return SimpleNamespace(_hidden_params={}, usage=SimpleNamespace(cost=cost),
                           choices=[SimpleNamespace(message=SimpleNamespace(
                               content=content, model_dump=lambda: message.copy()))])


def test_load_results_ignores_usage_and_deduplicates_revisions(tmp_path):
    cfg = config(tmp_path)
    (tmp_path / "usage.jsonl").write_text('{"cost": 1}\n')
    (tmp_path / "notes.jsonl").write_text('not a checkpoint\n')
    name = utils.get_ckpt_name(cfg, add_time=False)
    utils.save_checkpoint(str(tmp_path / f"{name}_20260907010000.jsonl"),
                          [row(reward=None), row(retry_exhausted=True)])
    loaded = utils.load_results(cfg, ["0"])
    assert len(loaded) == 1
    assert loaded[0].retry_exhausted
    assert loaded[0].trial_id == 1


@pytest.mark.parametrize("change", [
    {"model": "gemini/gemini-2.5-flash"}, {"api_base": "http://other-provider"},
    {"validation_model": "other"}, {"validation_trials": 2}, {"max_agent_turns": 4},
    {"timeout": 21}, {"max_retry": 2}, {"reasoning_effort": "high"},
    {"max_completion_tokens": 100}, {"reward_scope": "final"},
])
def test_checkpoint_identity_distinguishes_runtime_settings(tmp_path, change):
    assert utils.get_ckpt_name(config(tmp_path), False) != utils.get_ckpt_name(config(tmp_path, **change), False)


def test_checkpoint_loader_matches_whole_identity(tmp_path):
    cfg = config(tmp_path)
    name = utils.get_ckpt_name(cfg, False)
    utils.save_checkpoint(str(tmp_path / f"prefix-{name}_20260907010000.jsonl"), [row()])
    assert utils.load_results(cfg, ["0"]) == []


def test_cost_fallback_and_unknown_accounting():
    assert utils.response_cost(response(cost=0.25)) == 0.25
    res = response(cost=0.25)
    res._hidden_params = {"response_cost": 0.0}
    assert utils.response_cost(res) == 0.0
    assert utils.response_cost(response(cost=None)) is None
    assert utils.add_costs(0.1, None) is None


def test_reasoning_and_request_timeout_reach_completion(monkeypatch):
    calls = []
    monkeypatch.setattr(utils, "completion", lambda **kwargs: calls.append(kwargs) or response())
    utils.get_completion("openrouter/google/gemini-2.5-flash", [], 0.0,
                         reasoning_effort="high", max_completion_tokens=101, timeout=7)
    assert calls[0]["reasoning_effort"] == "high"
    assert calls[0]["max_completion_tokens"] == 101
    assert calls[0]["include_reasoning"] is True
    assert "reasoning_effort" in calls[0]["allowed_openai_params"]
    assert calls[0]["timeout"] == 7
    assert calls[0]["num_retries"] == 0


def test_user_cost_uses_provider_usage(monkeypatch):
    monkeypatch.setattr("src.envs.user.get_completion", lambda **kwargs: response("Hello", 0.4))
    user = LLMUser("gemini/gemini-2.5-flash")
    assert user.generate_next_message([]) == "Hello"
    assert user.get_total_cost() == 0.4


@pytest.mark.parametrize("valid_second", [True, False])
def test_validator_retries_parse_errors_and_never_passes_failure(monkeypatch, valid_second):
    calls = []
    good = json.dumps(dict(explanation="", evidence="", broken_rule="", result="no_error"))
    def complete(**kwargs):
        calls.append(kwargs)
        return response(good if valid_second and len(calls) == 2 else "{bad", cost=0.1)
    monkeypatch.setattr(validator, "get_completion", complete)
    monkeypatch.setattr(utils.time, "sleep", lambda _: None)
    env = Env([], [task()], "human", "unused", 0.0, "unused", "incre", task_index="0")
    result = validator.user_validator([{"role": "user", "content": "hello"}],
                                      env, "gemini/gemini-2.5-flash")
    assert result.decision == ("no_error" if valid_second else "validator_error")
    assert 2 <= len(calls) <= 3
    assert result.eval_cost == round(0.1 * len(calls), 8)


def test_agent_timeout_preserves_executed_tool_and_cost(monkeypatch, tmp_path):
    clock = [0.0]
    monkeypatch.setattr(utils.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(utils.time, "sleep", lambda _: None)
    calls = []
    def complete(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return response(None, tool=True)
        clock[0] = 25.0
        raise TimeoutError("request deadline")
    monkeypatch.setattr(utils, "completion", complete)
    class SqlTool:
        @staticmethod
        def get_info():
            return {"function": {"name": "sql_execute"}}
        @staticmethod
        def invoke(query, timeout=60):
            assert query == "SELECT 1"
            assert timeout <= 20
            return "[(1,)]"
    env = Env([], [task()], "human", "unused", 0.0, str(tmp_path / "db"), "incre", task_index="0")
    monkeypatch.setattr(env, "tools_info", [SqlTool.get_info()])
    monkeypatch.setattr(env, "tools_map", {"sql_execute": SqlTool})
    monkeypatch.setattr(env.user, "reset", lambda _: "Count rows")
    agent = ToolCallingAgent(env.tools_info, "", "openrouter/google/gemini-2.5-flash")
    with pytest.raises(AgentTimeoutError) as error:
        agent.run(env, "0", max_num_steps=3, agent_timeout=20)
    partial = error.value.result
    assert partial is not None
    assert partial.messages[-1]["role"] == "tool"
    assert partial.messages[-1]["content"] == "[(1,)]"
    assert partial.agent_cost == 0.25
    assert calls[-1]["timeout"] <= 20


def test_retry_wait_is_bounded_by_deadline(monkeypatch):
    clock = [0.0]
    waits = []
    monkeypatch.setattr(utils.time, "monotonic", lambda: clock[0])
    def wait(seconds):
        waits.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(utils.time, "sleep", wait)
    def fail(**kwargs):
        raise RuntimeError("provider unavailable")
    monkeypatch.setattr(utils, "completion", fail)
    with pytest.raises(AgentTimeoutError):
        utils.get_action("openrouter/google/gemini-2.5-flash", [], 0.0, deadline=2.0)
    assert sum(waits) <= 2.0


@pytest.mark.parametrize("args", [["--trial_id", "0"], ["--trial_id", "2", "--num_trials", "2"]])
def test_cli_rejects_invalid_trial_slots(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["run.py", "--model", "gpt-4o", "--agent_strategy", "tool-calling", *args])
    with pytest.raises(SystemExit):
        runner.parse_arguments()


def test_cli_accepts_explicit_trial_and_reasoning(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run.py", "--model", "gpt-4o", "--agent_strategy", "tool-calling",
        "--num_trials", "1", "--trial_id", "3", "--reasoning_effort", "high",
        "--max_completion_tokens", "100", "--reward_scope", "final"])
    cfg = runner.parse_arguments()
    assert (cfg.trial_id, cfg.reasoning_effort, cfg.max_completion_tokens, cfg.reward_scope) == (3, "high", 100, "final")


def install_runtime(monkeypatch, tmp_path):
    database = tmp_path / "test.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE example (id INTEGER)")

    def environment(**kwargs):
        tool = SQLExecute(engine=create_engine(f"sqlite:///{database}"))
        env = Env([], [task()], "human", "unused", 0.0, str(database), "incre", task_index="0")
        monkeypatch.setattr(env, "tools_info", [tool.get_info()])
        monkeypatch.setattr(env, "tools_map", {"sql_execute": tool})
        monkeypatch.setattr(env.user, "reset", lambda _: "Count rows")
        monkeypatch.setattr(env.user, "step", lambda _: "###END###")
        return env

    def complete(**kwargs):
        if kwargs["messages"][-1]["role"] == "tool":
            return response("One row", cost=0.2)
        return response(None, cost=0.1, tool=True)

    monkeypatch.setattr(runner, "get_env", environment)
    monkeypatch.setattr(utils, "completion", complete)
    monkeypatch.setattr(runner, "user_validator", lambda **kwargs: ValidationResult(
        decision="no_error", reason="", eval_cost=0.3))


def test_runner_preserves_trajectory_on_validator_exception(monkeypatch, tmp_path):
    install_runtime(monkeypatch, tmp_path)
    def fail(**kwargs):
        raise RuntimeError("validator unavailable")
    monkeypatch.setattr(runner, "user_validator", fail)
    cfg = config(tmp_path)
    with pytest.raises(ValueError):
        runner._run_single(cfg)
    stored, = utils.load_results(cfg, ["0"])
    assert stored.reward is None
    assert stored.validation is not None
    assert stored.validation.decision == "validator_error"
    assert any(message["role"] == "tool" for message in stored.messages)
    assert stored.cost.agent_cost == 0.3
    assert stored.cost.eval_cost is None
    assert stored.cost.total_cost is None


def test_runner_keeps_retry_attempt_costs_and_trial_id(monkeypatch, tmp_path):
    from metric import calculate_metrics
    install_runtime(monkeypatch, tmp_path)
    decisions = iter(["user_error", "no_error"])
    monkeypatch.setattr(runner, "user_validator", lambda **kwargs: ValidationResult(
        decision=next(decisions), reason="{}", eval_cost=0.3))
    cfg = config(tmp_path, max_retry=2, trial_id=4)
    runner._run_single(cfg)
    stored = utils.load_results(cfg, ["0"])
    assert [result.trial_id for result in stored] == [4, 4]
    assert [result.reward for result in stored] == [None, 1.0]
    assert len({result.sample_id for result in stored}) == 2
    metrics = calculate_metrics(stored, 1)
    assert metrics["costs"]["total"] == 1.2
    assert metrics["total_attempts"] == 2


def test_runner_resumes_the_missing_trial_slot_not_first_completion(monkeypatch, tmp_path):
    install_runtime(monkeypatch, tmp_path)
    cfg = config(tmp_path, num_trials=2)
    checkpoint = tmp_path / (utils.get_ckpt_name(cfg, False) + "_20260907010000.jsonl")
    utils.save_checkpoint(str(checkpoint), [row("completed-slot-2", trial_id=2)])
    runner._run_single(cfg)
    stored = utils.load_results(cfg, ["0"])
    assert len(stored) == 2
    assert {result.trial_id for result in stored} == {1, 2}
    assert next(result for result in stored if result.trial_id == 2).sample_id == "completed-slot-2"


def test_runner_rejects_unindexed_legacy_rows(monkeypatch, tmp_path):
    install_runtime(monkeypatch, tmp_path)
    cfg = config(tmp_path)
    checkpoint = tmp_path / (utils.get_ckpt_name(cfg, False) + "_20260907010000.jsonl")
    utils.save_checkpoint(str(checkpoint), [row(trial_id=None)])
    with pytest.raises(ValueError):
        runner._run_single(cfg)


def test_display_metrics_requires_missing_expected_tasks():
    with pytest.raises(ValueError):
        utils.display_metrics([row()], 1, expected_tasks={
            ("mimic_iv_star", "incre", "0"), ("mimic_iv_star", "incre", "1")})


def test_fingerprint_excludes_scope_but_full_scope_names_differ(tmp_path):
    first = config(tmp_path, task_ids=list(range(21)))
    second = config(tmp_path, task_ids=list(range(20)) + [25], num_trials=5, trial_id=None)
    assert utils.experiment_fingerprint(first) == utils.experiment_fingerprint(second)
    second.num_trials = first.num_trials
    assert utils.get_ckpt_name(first, False) != utils.get_ckpt_name(second, False)


def test_checkpoint_name_fits_filesystem_for_full_launcher_settings(tmp_path):
    cfg = config(tmp_path, trial_id=4, user_model="openrouter/google/gemini-2.5-flash-lite",
                 tool_mode="schema_removed", metadata_access="blocked", failure_feedback="detailed",
                 schema_guidance="identifier_free", embedding_model="openrouter/openai/text-embedding-3-small")
    path = tmp_path / (utils.get_ckpt_name(cfg) + ".jsonl")
    utils.save_checkpoint(str(path), [row()])
    assert utils.load_results(cfg, ["0"])[0].sample_id == "sample"


def test_runner_saves_timeout_without_discarding_tool_trajectory(monkeypatch, tmp_path):
    install_runtime(monkeypatch, tmp_path)
    def complete(**kwargs):
        if kwargs["messages"][-1]["role"] == "tool":
            raise TimeoutError("provider timeout")
        return response(None, cost=0.1, tool=True)
    monkeypatch.setattr(utils, "completion", complete)
    cfg = config(tmp_path)
    runner._run_single(cfg)
    stored, = utils.load_results(cfg, ["0"])
    assert stored.reward == 0.0
    assert stored.validation is not None
    assert stored.validation.decision == "agent_timeout"
    assert stored.messages[-1]["role"] == "tool"
    assert stored.cost.agent_cost == stored.cost.total_cost == 0.1


@pytest.mark.parametrize(("requested", "elapsed", "expected"), [
    (None, 199.0, 1.0), (0.5, 199.0, 0.5), (120, 0.0, 120.0), (None, 0.0, 60.0),
])
def test_sql_timeout_is_clamped_to_remaining_agent_budget(monkeypatch, requested, elapsed, expected):
    clock = [0.0]
    received = []
    monkeypatch.setattr(utils.time, "monotonic", lambda: clock[0])

    class SqlTool:
        @staticmethod
        def invoke(query, timeout=60):
            received.append((query, timeout))
            return "[(1,)]"

    def complete(**kwargs):
        clock[0] = elapsed
        result = response(None, tool=True)
        message = result.choices[0].message.model_dump()
        arguments = {"query": "SELECT 1"}
        if requested is not None:
            arguments["timeout"] = requested
        message["tool_calls"][0]["function"]["arguments"] = json.dumps(arguments)
        result.choices[0].message.model_dump = lambda: message
        return result

    monkeypatch.setattr(utils, "completion", complete)
    env = Env([], [task()], "human", "unused", 0.0, "unused", "incre", task_index="0")
    monkeypatch.setattr(env, "tools_map", {"sql_execute": SqlTool})
    monkeypatch.setattr(env.user, "reset", lambda _: "Count rows")
    agent = ToolCallingAgent([{"function": {"name": "sql_execute"}}], "", "openrouter/google/gemini-2.5-flash")
    result = agent.run(env, "0", max_num_steps=1, agent_timeout=200)
    assert received == [("SELECT 1", expected)]
    assert result.messages[-1]["content"] == "[(1,)]"


@pytest.mark.parametrize("stored_identity", [None, "matching", "mismatched"])
def test_checkpoint_row_identity_must_match_when_present(tmp_path, stored_identity):
    cfg = config(tmp_path)
    identity = utils.experiment_fingerprint(cfg) if stored_identity == "matching" else stored_identity
    path = tmp_path / (utils.get_ckpt_name(cfg) + ".jsonl")
    utils.save_checkpoint(str(path), [row(experiment_id=identity)])
    if stored_identity == "mismatched":
        with pytest.raises(ValueError):
            utils.load_results(cfg, ["0"])
    else:
        assert len(utils.load_results(cfg, ["0"])) == 1
