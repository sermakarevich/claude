#!/usr/bin/env python3
"""MCP server exposing PostgreSQL query tools for one or more named configs.

Each config is a JSON file in `credentials/` next to this script. Keys:
    host, port, database, user, password, read_only (bool, default true).
String values starting with `$` are resolved from the environment.
"""

import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from mcp.server.fastmcp import FastMCP

CREDENTIALS_DIR = Path(__file__).parent / "credentials"


def _load_configs() -> dict[str, dict]:
    if not CREDENTIALS_DIR.is_dir():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(CREDENTIALS_DIR.glob("*.json")):
        with path.open() as f:
            out[path.stem] = json.load(f)
    return out


_configs = _load_configs()
_names_hint = (
    f"\n\nAvailable configs: {', '.join(_configs.keys())}." if _configs else ""
)

mcp = FastMCP(
    "postgres",
    instructions=(
        "Query one or more configured PostgreSQL databases. Each connection is "
        "defined by a JSON file in the `credentials/` directory next to this server "
        "(host, port, database, user, password, read_only). "
        "Tools: `list_configs`, `list_schemas`, `list_tables`, `describe_table`, "
        "`execute_query`."
        + _names_hint
    ),
)


def _resolve(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return os.environ.get(value[1:], "")
    return value


def _connect(config_name: str) -> psycopg.Connection:
    if config_name not in _configs:
        available = ", ".join(_configs.keys()) or "(none)"
        raise ValueError(f"Unknown config '{config_name}'. Available: {available}")
    cfg = _configs[config_name]
    kwargs: dict[str, Any] = {
        "host": _resolve(cfg.get("host", "localhost")),
        "port": int(_resolve(cfg.get("port", 5432))),
        "dbname": _resolve(cfg["database"]),
        "user": _resolve(cfg["user"]),
        "password": _resolve(cfg.get("password", "")),
    }
    if cfg.get("read_only", True):
        kwargs["options"] = "-c default_transaction_read_only=on"
    return psycopg.connect(**kwargs)


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return str(value)


@mcp.tool()
def list_configs() -> list[str]:
    """List the names of available database configurations."""
    return list(_configs.keys())


@mcp.tool()
def list_schemas(config: str) -> list[str]:
    """List user schemas in the database (excludes pg_* and information_schema).

    Args:
        config: Configuration name (from `list_configs`).
    """
    sql = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
          AND schema_name NOT LIKE 'pg_%'
        ORDER BY schema_name
    """
    with _connect(config) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


@mcp.tool()
def list_tables(config: str, schema: str = "public") -> list[dict]:
    """List tables and views in a schema.

    Args:
        config: Configuration name.
        schema: Schema name. Default: "public".
    """
    sql = """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name
    """
    with _connect(config) as conn, conn.cursor() as cur:
        cur.execute(sql, (schema,))
        return [
            {"schema": r[0], "name": r[1], "kind": r[2]}
            for r in cur.fetchall()
        ]


@mcp.tool()
def describe_table(config: str, table: str, schema: str = "public") -> list[dict]:
    """Show column info for a table.

    Args:
        config: Configuration name.
        table: Table name.
        schema: Schema name. Default: "public".
    """
    sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """
    with _connect(config) as conn, conn.cursor() as cur:
        cur.execute(sql, (schema, table))
        return [
            {
                "name": r[0],
                "type": r[1],
                "nullable": r[2] == "YES",
                "default": r[3],
            }
            for r in cur.fetchall()
        ]


@mcp.tool()
def execute_query(config: str, sql: str, limit: int = 1000) -> dict:
    """Execute a SQL statement against the named database.

    Args:
        config: Configuration name.
        sql: SQL to run. Writes are blocked when the config has `read_only`
            set to true (the default).
        limit: Max rows fetched for result-returning statements. Default: 1000.

    Returns:
        For SELECT-like statements: {"columns": [...], "rows": [...], "row_count": N}.
        For statements with no result set: {"affected": N}.
    """
    with _connect(config) as conn, conn.cursor() as cur:
        cur.execute(sql)
        if cur.description is None:
            return {"affected": cur.rowcount}
        cols = [d.name for d in cur.description]
        rows = cur.fetchmany(limit)
        return {
            "columns": cols,
            "rows": [[_to_jsonable(v) for v in r] for r in rows],
            "row_count": len(rows),
        }


if __name__ == "__main__":
    mcp.run()
