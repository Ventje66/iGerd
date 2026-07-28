"""Versioned, checksummed, idempotent schema migrations.

The single most useful thing you can give a model that writes Cypher is a place to
put DDL where it will be applied exactly once, in order, and noticed if it changes
after the fact. Without it, schema drifts by ad-hoc statements pasted into a shell
and nobody can say what shape the production graph is actually in.

Layout::

    schema/migrations/
        001_core_schema/
            neo4j.cypher
            kuzu.cypher
        003_backfill_segments/
            shared.cypher      # used when both dialects agree

Applied versions are recorded as ``SchemaMigration`` nodes in the graph itself, so
the database always knows its own version.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .backend import Backend, split_statements

BOOTSTRAP: dict[str, list[str]] = {
    "kuzu": [
        """CREATE NODE TABLE IF NOT EXISTS SchemaMigration(
               version STRING,
               name STRING,
               checksum STRING,
               applied_at STRING,
               PRIMARY KEY(version)
           )"""
    ],
    "neo4j": [
        """CREATE CONSTRAINT schema_migration_version_unique IF NOT EXISTS
           FOR (m:SchemaMigration) REQUIRE m.version IS UNIQUE"""
    ],
}


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    script: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.script.encode("utf-8")).hexdigest()[:16]

    @property
    def statements(self) -> list[str]:
        return split_statements(self.script)


class MigrationError(RuntimeError):
    pass


def discover(migrations_dir: Path, dialect: str) -> list[Migration]:
    """Load migrations for a dialect, ordered by version.

    A version directory with neither ``<dialect>.cypher`` nor ``shared.cypher`` is
    an error, not a skip: silently doing nothing on one engine is how two
    deployments of the same repo end up with different graphs.
    """
    migrations: list[Migration] = []
    for directory in sorted(p for p in migrations_dir.iterdir() if p.is_dir()):
        version, _, name = directory.name.partition("_")
        specific = directory / f"{dialect}.cypher"
        shared = directory / "shared.cypher"
        source = specific if specific.exists() else shared
        if not source.exists():
            raise MigrationError(
                f"{directory.name} has no {dialect}.cypher and no shared.cypher"
            )
        migrations.append(
            Migration(
                version=version,
                name=name or directory.name,
                path=source,
                script=source.read_text(encoding="utf-8"),
            )
        )
    return migrations


def applied(backend: Backend) -> dict[str, str]:
    """Return ``{version: checksum}`` for migrations already applied."""
    backend.run_script(BOOTSTRAP[backend.dialect])
    rows = backend.run(
        "MATCH (m:SchemaMigration) RETURN m.version AS version, m.checksum AS checksum"
    )
    return {row["version"]: row["checksum"] for row in rows}


def status(backend: Backend, migrations_dir: Path) -> list[tuple[Migration, str]]:
    """Pair every migration with ``applied`` / ``pending`` / ``CHANGED``."""
    seen = applied(backend)
    report: list[tuple[Migration, str]] = []
    for migration in discover(migrations_dir, backend.dialect):
        if migration.version not in seen:
            state = "pending"
        elif seen[migration.version] != migration.checksum:
            state = "CHANGED"
        else:
            state = "applied"
        report.append((migration, state))
    return report


def migrate(backend: Backend, migrations_dir: Path) -> list[Migration]:
    """Apply pending migrations in order. Returns the ones that ran."""
    seen = applied(backend)
    ran: list[Migration] = []

    for migration in discover(migrations_dir, backend.dialect):
        if migration.version in seen:
            if seen[migration.version] != migration.checksum:
                # Editing an applied migration means the database and the repo
                # disagree about what was run. Refuse loudly: the fix is a new
                # migration, never a quiet edit to an old one.
                raise MigrationError(
                    f"migration {migration.version} was modified after it was applied "
                    f"(recorded {seen[migration.version]}, file is {migration.checksum}). "
                    "Add a new migration instead of editing an applied one."
                )
            continue

        statements = migration.statements
        if statements:
            backend.run_script(statements)
        backend.run(
            """CREATE (m:SchemaMigration {
                   version: $version,
                   name: $name,
                   checksum: $checksum,
                   applied_at: $applied_at
               })""",
            {
                "version": migration.version,
                "name": migration.name,
                "checksum": migration.checksum,
                "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
        ran.append(migration)

    return ran
