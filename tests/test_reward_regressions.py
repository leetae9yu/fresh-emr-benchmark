import sqlite3
from pathlib import Path
from ast import literal_eval
from collections.abc import Callable, Iterator
from typing import Never

from func_timeout import FunctionTimedOut

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from src.envs.base import Env
from src.envs.eicu_star.tools.sql_execute import SQLExecute as EicuSQLExecute
from src.envs.mimic_iv_star.tools.sql_execute import SQLExecute as MimicSQLExecute
from src.experiment import ExperimentConfig, FailureFeedback, MetadataAccess, RewardScope, open_sqlite_database
from src.types import Action, Task


@pytest.fixture(params=[EicuSQLExecute, MimicSQLExecute])
def environment(request: pytest.FixtureRequest, tmp_path: Path,
                monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    database = tmp_path / "reward.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE records (value INTEGER)")
        connection.executemany("INSERT INTO records VALUES (?)", [(1,), (1,), (2,), (None,)])
    engine = create_engine(
        "sqlite://",
        creator=lambda: open_sqlite_database(str(database), MetadataAccess.BLOCKED),
        poolclass=NullPool,
    )
    env = Env(
        tools=[request.param(engine=engine)],
        tasks=[Task(db_id="test", task_id="1", task_type="adapt", instruction="",
                    gold_sql="SELECT 1", gold_answer=[[1]])],
        user_strategy="human", user_model="unused", user_temperature=0.0,
        db_path=str(database), task_type="adapt", task_index="0",
    )
    monkeypatch.setattr(env.user, "step", lambda content: "###END###")
    monkeypatch.setattr(env.user, "reset", lambda task: "")
    yield env
    engine.dispose()


@pytest.mark.parametrize(("gold", "answer", "expected"), [
    (1, "10", 0.0), ("two", "2000", 0.0),
    (1, "1.5", 0.0), (1, "-1", 0.0), (1, "100%", 0.0),
    (1, "1.0000", 1.0), (2.5, "2.5000 days", 1.0),
    (41.6667, "41.6667%", 1.0), ("two", "two", 1.0),
    ("two", "2", 1.0), ("two", "2.0000", 1.0),
    ("prednisone", "Prednisone", 1.0),
    ("famotidine, pepcid", "famotidine, pepcid", 1.0),
    ("030-10194", "030-10194", 1.0),
    ("2100-06-15 08:30:00", "2100-06-15 08:30:00", 1.0),
])
def test_adapt_matches_exact_values(environment: Env, gold: str | float,
                                    answer: str, expected: float) -> None:
    # Given
    environment.task.gold_answer = [[gold]]
    # When
    result = environment.step(Action(name="respond", kwargs={"content": f"<answer>{answer}</answer>"}))
    # Then
    assert result.done
    assert result.reward == expected


@pytest.mark.parametrize("answer", ["2 and 1", "1.0; 2.000", "1, 2"])
def test_adapt_preserves_unordered_lists(environment: Env, answer: str) -> None:
    # Given
    environment.task.gold_answer = [[1], [2]]
    # When
    result = environment.step(Action(name="respond", kwargs={"content": f"<answer>{answer}</answer>"}))
    # Then
    assert result.reward == 1.0


@pytest.mark.parametrize("feedback", list(FailureFeedback))
def test_incre_rejects_sql_blocked_by_live_policy(environment: Env, feedback: FailureFeedback,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    environment.task_type = "incre"
    monkeypatch.setattr(environment.tools_map["sql_execute"], "failure_feedback", feedback)
    # When
    observation = environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 1 FROM sqlite_master"}))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert observation.observation != "[(1,)]"
    assert result.reward == 0.0


@pytest.mark.parametrize(("scope", "expected"), [("any", 1.0), ("final", 0.0)])
@pytest.mark.parametrize("last_answer", ["<answer>2</answer>", "unformatted", ""])
def test_adapt_scope_uses_latest_response(environment: Env, monkeypatch: pytest.MonkeyPatch,
                                        scope: str, expected: float, last_answer: str) -> None:
    # Given
    environment.experiment = ExperimentConfig(reward_scope=RewardScope(scope))
    replies = iter(["", "###END###"])
    monkeypatch.setattr(environment.user, "step", lambda content: next(replies))
    # When
    environment.step(Action(name="respond", kwargs={"content": "<answer>1</answer>"}))
    result = environment.step(Action(name="respond", kwargs={"content": last_answer}))
    # Then
    assert result.reward == expected


@pytest.mark.parametrize(("scope", "expected"), [("any", 1.0), ("final", 0.0)])
@pytest.mark.parametrize("last_query", ["SELECT 2", "SELECT 1 FROM sqlite_master", "SELECT * FROM absent"])
def test_incre_scope_uses_latest_sql(environment: Env, scope: str,
                                   expected: float, last_query: str) -> None:
    # Given
    environment.task_type = "incre"
    environment.experiment = ExperimentConfig(reward_scope=RewardScope(scope))
    # When
    environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 1"}))
    environment.step(Action(name="sql_execute", kwargs={"query": last_query}))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert result.reward == expected


def test_incre_preserves_set_and_any_column_comparison(environment: Env) -> None:
    # Given
    environment.task_type = "incre"
    environment.task.gold_answer = [[1], [2]]
    # When
    environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 99, value FROM records ORDER BY value DESC"}))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert result.reward == 1.0


def test_incre_does_not_reexecute_sql(environment: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    environment.task_type = "incre"
    environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 1"}))

    def unexpected_connection(*args, **kwargs):
        pytest.fail("Reward calculation must use the live observation")

    monkeypatch.setattr(sqlite3, "connect", unexpected_connection)
    # When
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert result.reward == 1.0


def test_incre_reset_discards_execution_history(environment: Env) -> None:
    # Given
    environment.task_type = "incre"
    environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 1"}))
    # When
    environment.reset(task_index="0")
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert result.reward == 0.0


@pytest.mark.parametrize("k", [0, 1])
def test_incre_scores_full_live_rows_despite_display_limit(environment: Env, k: int) -> None:
    # Given
    environment.task_type = "incre"
    environment.task.gold_answer = [[1], [2]]
    # When
    observation = environment.step(Action(name="sql_execute", kwargs={
        "query": "SELECT DISTINCT value FROM records WHERE value IS NOT NULL ORDER BY value", "k": k,
    }))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert literal_eval(observation.observation.split("\n\n")[0]) == [(1,)][:k]
    assert result.reward == 1.0


def test_incre_sorts_full_result_before_benchmark_cap(environment: Env) -> None:
    # Given
    environment.task_type = "incre"
    environment.task.gold_answer = [[value] for value in range(1, 102)]
    query = ("WITH RECURSIVE numbers(value) AS (SELECT 1 UNION ALL "
             "SELECT value + 1 FROM numbers WHERE value < 101) "
             "SELECT value FROM numbers ORDER BY value DESC")
    # When
    observation = environment.step(Action(name="sql_execute", kwargs={"query": query}))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert literal_eval(observation.observation.split("\n\n")[0]) == [(value,) for value in range(101, 1, -1)]
    assert result.reward == 1.0


@pytest.mark.parametrize("kwargs", [
    {"query": "SELECT 1 FROM sqlite_master"},
    {"query": "SELECT * FROM absent"},
    {"query": "SELECT 1", "k": "invalid"},
    {},
])
def test_incre_failed_attempt_cannot_reuse_full_result(environment: Env, kwargs: dict[str, str]) -> None:
    # Given
    environment.task_type = "incre"
    environment.experiment = ExperimentConfig(reward_scope=RewardScope.FINAL)
    environment.step(Action(name="sql_execute", kwargs={"query": "SELECT 1", "k": 0}))
    # When
    environment.step(Action(name="sql_execute", kwargs=kwargs))
    result = environment.step(Action(name="respond", kwargs={"content": ""}))
    # Then
    assert result.reward == 0.0


@pytest.mark.parametrize("tool_type", [EicuSQLExecute, MimicSQLExecute])
def test_sql_result_cache_is_instance_local(tool_type: type[EicuSQLExecute] | type[MimicSQLExecute]) -> None:
    # Given
    engine = create_engine("sqlite://", poolclass=NullPool)
    first, second = tool_type(engine=engine), tool_type(engine=engine)
    try:
        # When
        first.invoke("SELECT 1", k=0)
        second.invoke("SELECT 2", k=0)
        # Then
        assert first.last_result == "[(1,)]"
        assert second.last_result == "[(2,)]"
    finally:
        engine.dispose()


@pytest.mark.parametrize("tool_type", [EicuSQLExecute, MimicSQLExecute])
def test_sql_failed_call_clears_full_result(tool_type: type[EicuSQLExecute] | type[MimicSQLExecute]) -> None:
    # Given
    engine = create_engine("sqlite://", poolclass=NullPool)
    tool = tool_type(engine=engine)
    try:
        tool.invoke("SELECT 1", k=0)
        # When
        tool.invoke("SELECT * FROM absent")
        # Then
        assert tool.last_result is None
    finally:
        engine.dispose()


@pytest.mark.parametrize("tool_type", [EicuSQLExecute, MimicSQLExecute])
def test_sql_timeout_cannot_publish_full_result(tool_type: type[EicuSQLExecute] | type[MimicSQLExecute],
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    engine = create_engine("sqlite://", poolclass=NullPool)
    tool = tool_type(engine=engine)
    try:
        tool.invoke("SELECT 1", k=0)

        def expired(timeout: int, function: Callable[[], None]) -> Never:
            function()
            raise FunctionTimedOut(timedOutAfter=timeout)

        monkeypatch.setattr(f"{tool_type.__module__}.func_timeout", expired)
        # When
        tool.invoke("SELECT 2", k=0)
        # Then
        assert tool.last_result is None
    finally:
        engine.dispose()
