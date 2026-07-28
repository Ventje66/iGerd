"""Backend abstraction over two Cypher engines.

The abstraction is deliberately thin. It hides *connection* differences, not
*dialect* differences: read queries are shared verbatim, DDL is written once per
dialect under ``schema/migrations/``. Papering over dialect differences in code is
how you end up unable to tell which engine a bug belongs to.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Protocol, runtime_checkable

Row = dict[str, Any]

_LINE_COMMENT = re.compile(r"//[^\n]*")


def split_statements(script: str) -> list[str]:
    """Split a .cypher file into individual statements.

    Strips ``//`` line comments, then splits on ``;``. Semicolons inside string
    literals would break this; none of the migrations use them, and a migration
    that needs one should be a parameterised call from Python instead.
    """
    without_comments = _LINE_COMMENT.sub("", script)
    return [stmt.strip() for stmt in without_comments.split(";") if stmt.strip()]


@runtime_checkable
class Backend(Protocol):
    """Everything the rest of the package is allowed to assume about a database."""

    dialect: str

    def run(self, cypher: str, params: Row | None = None) -> list[Row]:
        """Execute one statement and materialise its rows."""

    def run_script(self, statements: Iterable[str]) -> None:
        """Execute statements in order, atomically where the engine allows it."""

    def close(self) -> None: ...


def get_backend(dialect: str, **kwargs: Any) -> Backend:
    """Construct a backend by dialect name."""
    if dialect == "kuzu":
        from .backends.kuzu_backend import KuzuBackend

        return KuzuBackend(**kwargs)
    if dialect == "neo4j":
        from .backends.neo4j_backend import Neo4jBackend

        return Neo4jBackend(**kwargs)
    raise ValueError(f"unknown backend dialect: {dialect!r} (expected 'kuzu' or 'neo4j')")
