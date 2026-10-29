"""Thin Postgres access layer (psycopg 3 pool, dict rows). Domain helpers live in db.py."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from config import settings

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=True,
        )
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def tx() -> Iterator[Connection]:
    """Explicit transaction: everything inside commits or rolls back together."""
    with pool().connection() as conn:
        with conn.transaction():
            yield conn


def all_rows(sql: str, params: Any = None) -> list[dict]:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchall()


def one(sql: str, params: Any = None) -> dict | None:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchone()


def run(sql: str, params: Any = None) -> int:
    with pool().connection() as conn:
        return conn.execute(sql, params).rowcount


def run_script(sql: str) -> None:
    """Execute a multi-statement SQL file (no parameters)."""
    with pool().connection() as conn:
        conn.execute(sql)


json = Jsonb
