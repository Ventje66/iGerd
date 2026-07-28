"""Server backend. Same queries, real deployment.

Bring one up with ``docker compose up -d`` and point ``NEO4J_URI`` at it; the CLI
and the whole test suite then run against Neo4j unchanged. If a query passes on
Kuzu and fails here, the difference is a dialect fact worth writing down in
``schema/model.md`` — not something to smooth over in this file.
"""

from __future__ import annotations

from typing import Any, Iterable

from neo4j import GraphDatabase

from ..backend import Row


class Neo4jBackend:
    dialect = "neo4j"

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._driver.verify_connectivity()

    def run(self, cypher: str, params: Row | None = None) -> list[Row]:
        with self._driver.session(database=self._database) as session:
            return [record.data() for record in session.run(cypher, params or {})]

    def run_script(self, statements: Iterable[str]) -> None:
        # Schema and data statements cannot share a transaction in Neo4j, so each
        # statement is its own unit. A migration that fails halfway leaves the
        # earlier statements applied — which is exactly why every migration
        # statement in this repo is written to be idempotent (IF NOT EXISTS,
        # MERGE, or a WHERE-guarded SET) and why the runner records the version
        # only after the whole file succeeds.
        with self._driver.session(database=self._database) as session:
            for statement in statements:
                session.run(statement).consume()

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jBackend":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
