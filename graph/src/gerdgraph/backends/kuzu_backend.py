"""Embedded backend. No server, no container, no fixture teardown to get wrong.

This is what makes the test suite worth having: a full migrate + ingest + query
cycle against a real Cypher engine costs a few hundred milliseconds and a temp file,
so every query in the library can afford its own test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import kuzu

from ..backend import Row


class KuzuBackend:
    dialect = "kuzu"

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(self._db)

    def run(self, cypher: str, params: Row | None = None) -> list[Row]:
        result = self._conn.execute(cypher, params or {})
        # A statement may produce several result sets; only the last carries rows
        # we care about, and DDL carries none.
        if isinstance(result, list):
            result = result[-1]
        columns = result.get_column_names()
        return [dict(zip(columns, row)) for row in result]

    def run_script(self, statements: Iterable[str]) -> None:
        statements = list(statements)
        # Kuzu rolls back DDL on failure only inside an explicit transaction, and
        # refuses to nest one, so guard the whole script and unwind by hand.
        self._conn.execute("BEGIN TRANSACTION")
        try:
            for statement in statements:
                self._conn.execute(statement)
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def close(self) -> None:
        self._conn.close()
        self._db.close()

    def __enter__(self) -> "KuzuBackend":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
