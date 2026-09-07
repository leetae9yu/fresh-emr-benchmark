import importlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import src.experiment as experiment_module
from src.envs.rules import rules, task_type_adaptive, task_type_incremental
from src.experiment import (
    DEFAULT_EXPERIMENT_CONFIG,
    ExperimentConfig,
    FailureFeedback,
    MetadataAccess,
    SchemaGuidance,
    ToolMode,
)

FULL_TOOLS = [
    "table_search", "column_search", "sql_execute", "value_substring_search",
    "value_similarity_search", "web_search",
]
REMOVED_TOOLS = FULL_TOOLS[2:]


class BoundaryVectorStore(FAISS):
    """Only replace embedding/index I/O; exercise the real similarity tool."""

    def __init__(self):
        super().__init__(
            embedding_function=lambda text: [0.0],
            index=SimpleNamespace(ntotal=1),
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )
        self.calls = []

    def similarity_search(self, query, k=4, filter=None, fetch_k=20, **kwargs):
        self.calls.append((query, k, filter, fetch_k))
        return [Document(page_content="aspirin", metadata=filter)]


@pytest.fixture(params=[
    ("mimic_iv", "MimicIVEnv"),
    ("mimic_iv_star", "MimicIVStarEnv"),
    ("eicu", "eICUEnv"),
    ("eicu_star", "eICUStarEnv"),
])
def environment_factory(request, monkeypatch, tmp_path):
    name, class_name = request.param
    module = importlib.import_module(f"src.envs.{name}.env")
    database = tmp_path / "database.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE medications (drug TEXT)")
        connection.execute("INSERT INTO medications VALUES ('aspirin')")
    vector_store = BoundaryVectorStore()
    builds = []
    verified = []
    web_queries = []

    def initialize(engine, embedding_model, faiss_path, columns):
        builds.append((embedding_model, faiss_path, columns))
        return vector_store

    def web_invoke(self, query, **kwargs):
        web_queries.append(query)
        return [{"content": "boundary-result"}]

    monkeypatch.setattr(module, "initialize_vector_store", initialize)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(TavilySearchResults, "invoke", web_invoke)
    if not name.endswith("_star"):
        monkeypatch.setattr(
            module, "verify_original_database",
            lambda *args: verified.append(args),
        )

    def make(config=DEFAULT_EXPERIMENT_CONFIG, task_type="incre"):
        return getattr(module, class_name)(
            user_strategy="human", user_model="unused", user_temperature=0.0,
            task_type=task_type, task_index=None, db_path=str(database),
            embedding_model="openrouter/openai/text-embedding-3-small",
            experiment=config,
        )

    return SimpleNamespace(
        make=make, module=module, name=name, builds=builds,
        vector_store=vector_store, verified=verified, web_queries=web_queries,
    )


@pytest.mark.parametrize("task_type", ["incre", "adapt"])
def test_full_preserves_shipped_tools_and_guidance(environment_factory, task_type):
    case = environment_factory
    env = case.make(task_type=task_type)
    assert list(env.tools_map) == FULL_TOOLS
    assert [item["function"]["name"] for item in env.tools_info] == FULL_TOOLS
    grading = task_type_incremental if task_type == "incre" else task_type_adaptive
    shipped = Path(case.module.__file__).with_name("db_rules.txt").read_text()
    assert env.rule == rules + "\n\n" + grading + "\n\n" + shipped
    for name, class_name in [
        ("table_search", "TableSearch"), ("column_search", "ColumnSearch"),
        ("sql_execute", "SQLExecute"),
        ("value_substring_search", "ValueSubstringSearch"),
        ("web_search", "WebSearch"),
    ]:
        assert env.tools_map[name].get_info() == getattr(case.module, class_name).get_info()
    similarity = env.tools_map["value_similarity_search"]
    columns = case.builds[0][2]
    if case.name.endswith("_star"):
        shipped_similarity = case.module.ValueSimilaritySearch(vector_store=case.vector_store)
        assert similarity.get_info() == shipped_similarity.get_info()
    else:
        assert similarity.schema_description == "Supported columns: " + ", ".join(
            f"{table}: {names!r}" for table, names in columns.items()
        )
    assert len(case.builds) == 1
    assert case.builds[0][:2] == (
        "openrouter/openai/text-embedding-3-small",
        f"src/envs/{case.name}/faiss_index_{case.name}-text-embedding-3-small",
    )
    assert len(case.verified) == (0 if case.name.endswith("_star") else 1)


@pytest.mark.parametrize("metadata", list(MetadataAccess))
def test_schema_removed_exposes_exact_retained_tools(environment_factory, metadata):
    case = environment_factory
    config = ExperimentConfig(
        tool_mode=ToolMode("schema_removed"), metadata_access=metadata,
        schema_guidance=SchemaGuidance.IDENTIFIER_FREE,
        failure_feedback=FailureFeedback.BINARY,
    )
    env = case.make(config)
    full = case.make(replace(config, tool_mode=ToolMode.FULL))
    assert env.experiment is config
    assert list(env.tools_map) == REMOVED_TOOLS
    assert [item["function"]["name"] for item in env.tools_info] == REMOVED_TOOLS
    assert case.builds[0] == case.builds[1]
    similarity = env.tools_map["value_similarity_search"]
    full_similarity = full.tools_map["value_similarity_search"]
    assert similarity.schema_description is None
    assert full_similarity.schema_description is not None
    expected = full_similarity.model_copy(update={"schema_description": None})
    assert similarity.get_info() == expected.get_info()
    assert similarity.get_info() != full_similarity.get_info()
    for name in set(REMOVED_TOOLS) - {"value_similarity_search"}:
        assert env.tools_map[name].get_info() == full.tools_map[name].get_info()

    assert env.tools_map["sql_execute"].invoke("SELECT drug FROM medications") == "[('aspirin',)]"
    catalog = env.tools_map["sql_execute"].invoke("SELECT name FROM sqlite_master")
    assert catalog == ("[('medications',)]" if metadata is MetadataAccess.ALLOWED else "FAILED")
    assert "aspirin" in env.tools_map["value_substring_search"].invoke(
        table="medications", column="drug", value="spir",
    )
    assert "aspirin" in similarity.invoke(table="medications", column="drug", value="ASPIRIN")
    assert case.vector_store.calls == [
        ("aspirin", 100, {"table": "medications", "column": "drug"}, 1),
    ]
    assert json.loads(env.tools_map["web_search"].invoke("test-query")) == ["boundary-result"]
    assert case.web_queries == ["test-query"]


@pytest.mark.parametrize("guidance", list(SchemaGuidance))
@pytest.mark.parametrize("task_type", ["incre", "adapt"])
def test_schema_removed_routes_guidance(environment_factory, guidance, task_type):
    case = environment_factory
    env = case.make(ExperimentConfig(
        tool_mode=ToolMode("schema_removed"), schema_guidance=guidance,
    ), task_type=task_type)
    grading = task_type_incremental if task_type == "incre" else task_type_adaptive
    expected = rules + "\n\n" + grading
    if guidance is SchemaGuidance.BENCHMARK:
        expected += "\n\n" + Path(case.module.__file__).with_name("db_rules.txt").read_text()
    elif guidance is SchemaGuidance.IDENTIFIER_FREE:
        family = case.name.removesuffix("_star")
        expected += "\n\n" + Path(f"src/ablation_prompts/{family}/db_rules.txt").read_text()
    assert env.rule == expected


def test_reward_scope_config_contract():
    assert hasattr(DEFAULT_EXPERIMENT_CONFIG, "reward_scope")
    scope = experiment_module.RewardScope
    assert scope.ANY.value == "any"
    assert scope.FINAL.value == "final"
    assert DEFAULT_EXPERIMENT_CONFIG.reward_scope is scope.ANY
    assert replace(DEFAULT_EXPERIMENT_CONFIG, reward_scope=scope.FINAL).reward_scope is scope.FINAL


def test_reward_scope_reaches_base_environment(environment_factory, monkeypatch):
    case = environment_factory
    captured = {}
    original = case.module.Env.__init__

    def initialize(self, *args, **kwargs):
        captured.update(kwargs)
        original(self, *args, **kwargs)

    monkeypatch.setattr(case.module.Env, "__init__", initialize)
    config = ExperimentConfig(
        tool_mode=ToolMode.SQL_ONLY,
        reward_scope=experiment_module.RewardScope.FINAL,
    )
    env = case.make(config)
    assert captured.get("experiment") is config
    assert env.experiment.reward_scope is experiment_module.RewardScope.FINAL
    assert case.builds == []
