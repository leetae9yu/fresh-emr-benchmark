import json
import os
from typing import assert_never

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from src.envs.base import Env
from src.envs.eicu_star.tools.column_search import ColumnSearch
from src.envs.eicu_star.tools.sql_execute import SQLExecute
from src.envs.eicu_star.tools.table_search import TableSearch
from src.envs.eicu_star.tools.value_similarity_search import ValueSimilaritySearch
from src.envs.eicu_star.tools.value_substring_search import ValueSubstringSearch
from src.envs.eicu_star.tools.web_search import WebSearch
from src.experiment import (
    DEFAULT_EXPERIMENT_CONFIG,
    ExperimentConfig,
    SchemaGuidance,
    ToolMode,
    open_sqlite_database,
)
from src.types import Task
from src.utils import initialize_vector_store, parse_model_name

class eICUStarEnv(Env):
    def __init__(
        self,
        user_strategy: str,
        user_model: str,
        user_temperature: float,
        task_type: str,
        task_index: str | None,
        api_base: str | None = None,
        db_id: str = 'eicu_star',
        db_path: str = "src/envs/eicu_star/eicu_star.sqlite",
        embedding_model: str = "text-embedding-3-large",
        retry_reason: list[str] | None = None,
        experiment: ExperimentConfig = DEFAULT_EXPERIMENT_CONFIG,
    ) -> None:
        self.db_id = db_id
        self.experiment = experiment
        assert os.path.exists(db_path), f"Database file does not exist: {db_path}"
        self.folder_path = os.path.dirname(__file__)
        if user_strategy == 'human':
            tasks = None
        else:
            with open(os.path.join(self.folder_path, f"eval_{task_type}.jsonl"), "r") as f:
                tasks = [Task(**kwargs) for kwargs in json.load(f)]         

        from ..rules import rules
        if task_type == "incre":
            from ..rules import task_type_incremental
            rules += '\n\n' + task_type_incremental
        elif task_type == "adapt":
            from ..rules import task_type_adaptive
            rules += '\n\n' + task_type_adaptive
        match experiment.schema_guidance:
            case SchemaGuidance.BENCHMARK:
                with open(os.path.join(self.folder_path, "db_rules.txt"), "r") as f:
                    rules += '\n\n' + f.read()
            case SchemaGuidance.IDENTIFIER_FREE:
                with open(
                    "src/ablation_prompts/eicu/db_rules.txt",
                    "r",
                ) as f:
                    rules += '\n\n' + f.read()
            case SchemaGuidance.HIDDEN:
                pass
            case unreachable:
                assert_never(unreachable)

        engine = create_engine(
            "sqlite://",
            creator=lambda: open_sqlite_database(db_path, experiment.metadata_access),
            poolclass=NullPool,
        )
        sql_execute = SQLExecute(
            engine=engine,
            failure_feedback=experiment.failure_feedback,
        )
        match experiment.tool_mode:
            case ToolMode.SQL_ONLY:
                tools = [sql_execute]
            case ToolMode.SQL_VALUE:
                faiss_path = 'src/envs/eicu_star/faiss_index_eicu_star-'+parse_model_name(embedding_model)
                columns_to_retrieve = {
                    "allergy_reaction": ["drug_name", "allergy_name"],
                    "condition": ["condition_name"],
                    "fluid_balance": ["fluid_label"],
                    "lab": ["lab_name"],
                    "prescription": ["drug_name"],
                    "icupatient": ["ethnicity", "hospital_admission_source"],
                    "treatment": ["treatment_name"]
                }
                vector_store = initialize_vector_store(engine, embedding_model, faiss_path, columns_to_retrieve)
                value_similarity_search = ValueSimilaritySearch(
                    vector_store=vector_store,
                    schema_description=None,
                )
                tools = [sql_execute, value_similarity_search]
            case ToolMode.FULL:
                table_search = TableSearch(engine=engine)
                column_search = ColumnSearch(engine=engine)
                value_substring_search = ValueSubstringSearch(engine=engine)
                faiss_path = 'src/envs/eicu_star/faiss_index_eicu_star-'+parse_model_name(embedding_model)
                columns_to_retrieve = {
                    "allergy_reaction": ["drug_name", "allergy_name"],
                    "condition": ["condition_name"],
                    "fluid_balance": ["fluid_label"],
                    "lab": ["lab_name"],
                    "prescription": ["drug_name"],
                    "icupatient": ["ethnicity", "hospital_admission_source"],
                    "treatment": ["treatment_name"]
                }
                vector_store = initialize_vector_store(engine, embedding_model, faiss_path, columns_to_retrieve)
                value_similarity_search = ValueSimilaritySearch(vector_store=vector_store)
                web_search = WebSearch()
                tools = [
                    table_search,
                    column_search,
                    sql_execute,
                    value_substring_search,
                    value_similarity_search,
                    web_search,
                ]
            case unreachable:
                assert_never(unreachable)

        super().__init__(
            tools=tools,
            tasks=tasks,
            user_strategy=user_strategy,
            user_model=user_model,
            user_temperature=user_temperature,
            db_path=db_path,
            task_type=task_type,
            task_index=task_index,
            rule=rules,
            api_base=api_base,
            retry_reason=retry_reason
        )
