"""Migration runner behaviour.

The properties that matter: applied exactly once, in order, and loud when the repo
and the database disagree.
"""

from __future__ import annotations

import pytest

from gerdgraph.backend import Backend
from gerdgraph.config import MIGRATIONS_DIR
from gerdgraph.migrate import MigrationError, applied, discover, migrate, status


def test_discover_orders_by_version(empty_backend: Backend) -> None:
    versions = [m.version for m in discover(MIGRATIONS_DIR, empty_backend.dialect)]
    assert versions == sorted(versions)
    assert versions[0] == "001"


def test_every_migration_resolves_for_both_dialects() -> None:
    # A migration that exists for one engine and not the other is the bug this
    # catches: it would apply cleanly in CI and leave production unmigrated.
    for dialect in ("kuzu", "neo4j"):
        migrations = discover(MIGRATIONS_DIR, dialect)
        assert migrations, f"no migrations found for {dialect}"


def test_migrate_applies_all_then_nothing(empty_backend: Backend) -> None:
    first = migrate(empty_backend, MIGRATIONS_DIR)
    assert [m.version for m in first] == ["001", "002", "003"]

    second = migrate(empty_backend, MIGRATIONS_DIR)
    assert second == [], "migrate must be a no-op once everything is applied"


def test_migrate_records_checksums(empty_backend: Backend) -> None:
    ran = migrate(empty_backend, MIGRATIONS_DIR)
    recorded = applied(empty_backend)
    assert recorded == {m.version: m.checksum for m in ran}


def test_status_reports_pending_then_applied(empty_backend: Backend) -> None:
    before = status(empty_backend, MIGRATIONS_DIR)
    assert {state for _, state in before} == {"pending"}

    migrate(empty_backend, MIGRATIONS_DIR)

    after = status(empty_backend, MIGRATIONS_DIR)
    assert {state for _, state in after} == {"applied"}


def test_editing_an_applied_migration_is_refused(
    empty_backend: Backend, monkeypatch: pytest.MonkeyPatch
) -> None:
    migrate(empty_backend, MIGRATIONS_DIR)

    # Simulate someone editing 002 after it shipped.
    original = discover(MIGRATIONS_DIR, empty_backend.dialect)

    def tampered(_dir, _dialect):  # type: ignore[no-untyped-def]
        edited = []
        for migration in original:
            if migration.version == "002":
                migration = type(migration)(
                    version=migration.version,
                    name=migration.name,
                    path=migration.path,
                    script=migration.script + "\n// sneaky edit\n",
                )
            edited.append(migration)
        return edited

    monkeypatch.setattr("gerdgraph.migrate.discover", tampered)

    with pytest.raises(MigrationError, match="modified after it was applied"):
        migrate(empty_backend, MIGRATIONS_DIR)


def test_migration_creates_queryable_schema(migrated_backend: Backend) -> None:
    # An empty result proves the labels and relationship types resolve, which on a
    # schema-first engine means the DDL actually ran.
    assert migrated_backend.run("MATCH (c:Customer) RETURN c.id AS id") == []
    assert migrated_backend.run("MATCH (:Product)-[:IN_CATEGORY]->(:Category) RETURN 1 AS x") == []
