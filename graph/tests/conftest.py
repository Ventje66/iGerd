"""Fixtures.

The whole suite runs against a real Cypher engine on a temp file. That is the
design constraint that makes the rest of this work: if the tests needed a server,
you would write three of them and stop, and then nothing would be checking the
Cypher a model hands you.

Set ``GRAPH_BACKEND=neo4j`` (plus ``NEO4J_URI`` / ``NEO4J_PASSWORD``) to run the
identical suite against Neo4j. The ``graph`` fixture then wipes and rebuilds that
database, so point it at a scratch instance, never at anything you care about.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

from gerdgraph.backend import Backend, get_backend
from gerdgraph.config import DATA_DIR, MIGRATIONS_DIR, Settings
from gerdgraph.ingest import ingest_all, read_csv
from gerdgraph.migrate import migrate


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture
def empty_backend(settings: Settings, tmp_path: Path) -> Iterator[Backend]:
    """A migrated-from-nothing database, no data loaded."""
    if settings.dialect == "kuzu":
        backend = get_backend("kuzu", db_path=tmp_path / "test.kz")
    else:
        backend = get_backend("neo4j", **settings.backend_kwargs())
        backend.run("MATCH (n) DETACH DELETE n")
        _drop_neo4j_schema(backend)
    try:
        yield backend
    finally:
        backend.close()


@pytest.fixture
def migrated_backend(empty_backend: Backend) -> Backend:
    migrate(empty_backend, MIGRATIONS_DIR)
    return empty_backend


@pytest.fixture
def graph(migrated_backend: Backend) -> Backend:
    """Migrated and loaded with data/*.csv — the state every query test wants."""
    ingest_all(migrated_backend, DATA_DIR)
    return migrated_backend


@pytest.fixture(scope="session")
def csv_data() -> dict[str, list[dict[str, str]]]:
    """The source CSVs, for computing expected answers independently of Cypher."""
    return {
        name: read_csv(DATA_DIR / f"{name}.csv")
        for name in ("customers", "suppliers", "products", "orders", "order_lines")
    }


def _drop_neo4j_schema(backend: Backend) -> None:
    for row in backend.run("SHOW CONSTRAINTS YIELD name RETURN name"):
        backend.run(f"DROP CONSTRAINT {row['name']} IF EXISTS")
    for row in backend.run("SHOW INDEXES YIELD name, type RETURN name, type"):
        if row["type"] != "LOOKUP":
            backend.run(f"DROP INDEX {row['name']} IF EXISTS")


def pytest_report_header(config: pytest.Config) -> str:
    return f"graph backend: {os.environ.get('GRAPH_BACKEND', 'kuzu')}"
