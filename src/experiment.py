import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never


class ToolMode(StrEnum):
    FULL = "full"
    SQL_ONLY = "sql_only"
    SQL_VALUE = "sql_value"


class MetadataAccess(StrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class FailureFeedback(StrEnum):
    DETAILED = "detailed"
    BINARY = "binary"


class SchemaGuidance(StrEnum):
    BENCHMARK = "benchmark"
    IDENTIFIER_FREE = "identifier_free"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    tool_mode: ToolMode = ToolMode.FULL
    metadata_access: MetadataAccess = MetadataAccess.ALLOWED
    failure_feedback: FailureFeedback = FailureFeedback.DETAILED
    schema_guidance: SchemaGuidance = SchemaGuidance.BENCHMARK


DEFAULT_EXPERIMENT_CONFIG: Final = ExperimentConfig()
FAILED_RESPONSE: Final = "FAILED"

_CATALOG_TABLES: Final = frozenset(
    {
        "sqlite_master",
        "sqlite_schema",
        "sqlite_temp_master",
        "sqlite_temp_schema",
    }
)
_BLOCKED_METADATA_ACTIONS: Final = frozenset(
    {
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }
)
_BLOCKED_SCHEMA_PRAGMAS: Final = frozenset(
    {
        "collation_list",
        "database_list",
        "foreign_key_list",
        "function_list",
        "index_info",
        "index_list",
        "index_xinfo",
        "module_list",
        "pragma_list",
        "table_info",
        "table_list",
        "table_xinfo",
    }
)


def _metadata_authorizer(
    action_code: int,
    first_argument: str | None,
    second_argument: str | None,
    database_name: str | None,
    trigger_name: str | None,
) -> int:
    del database_name, trigger_name
    if action_code in _BLOCKED_METADATA_ACTIONS:
        return sqlite3.SQLITE_DENY
    if (
        action_code == sqlite3.SQLITE_PRAGMA
        and first_argument is not None
        and first_argument.lower() in _BLOCKED_SCHEMA_PRAGMAS
    ):
        return sqlite3.SQLITE_DENY
    if (
        action_code == sqlite3.SQLITE_READ
        and first_argument is not None
        and first_argument.lower() in _CATALOG_TABLES
    ):
        return sqlite3.SQLITE_DENY
    if (
        action_code == sqlite3.SQLITE_FUNCTION
        and second_argument is not None
        and second_argument.lower().startswith("pragma_")
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def open_sqlite_database(
    database_path: str,
    metadata_access: MetadataAccess,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{database_path}?immutable=1",
        uri=True,
    )
    match metadata_access:
        case MetadataAccess.ALLOWED:
            return connection
        case MetadataAccess.BLOCKED:
            connection.set_authorizer(_metadata_authorizer)
            return connection
        case unreachable:
            assert_never(unreachable)


def format_sql_failure(
    failure_feedback: FailureFeedback,
    detailed_message: str,
) -> str:
    match failure_feedback:
        case FailureFeedback.DETAILED:
            return detailed_message
        case FailureFeedback.BINARY:
            return FAILED_RESPONSE
        case unreachable:
            assert_never(unreachable)
