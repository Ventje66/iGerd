"""Command line entry point.

    python -m gerdgraph migrate
    python -m gerdgraph status
    python -m gerdgraph ingest
    python -m gerdgraph queries
    python -m gerdgraph run revenue_by_customer --limit 3
    python -m gerdgraph run customers_exposed_to_supplier --supplier-id S02

Every subcommand works against whichever backend ``GRAPH_BACKEND`` selects.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from .backend import Backend, get_backend
from .config import DATA_DIR, MIGRATIONS_DIR, Settings
from .ingest import ingest_all
from .migrate import migrate, status
from .queries import QUERIES


@contextlib.contextmanager
def open_backend(settings: Settings) -> Iterator[Backend]:
    backend = get_backend(settings.dialect, **settings.backend_kwargs())
    try:
        yield backend
    finally:
        backend.close()


def _print_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("(no rows)")
        return
    columns = list(rows[0])
    widths = {
        column: max(len(column), *(len(_fmt(row[column])) for row in rows))
        for column in columns
    }
    print("  ".join(column.ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(_fmt(row[column]).ljust(widths[column]) for column in columns))


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _coerce(value: str) -> Any:
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gerdgraph", description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="apply pending migrations")
    subparsers.add_parser("status", help="show migration state")
    subparsers.add_parser("ingest", help="load data/*.csv (idempotent)")
    subparsers.add_parser("queries", help="list the query library")

    run_parser = subparsers.add_parser("run", help="run a named query")
    run_parser.add_argument("name", choices=sorted(QUERIES))
    # Unknown flags become query parameters: --supplier-id S02 -> supplier_id="S02".
    run_parser.add_argument("params", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    settings = Settings.from_env()

    if args.command == "queries":
        for name, query in sorted(QUERIES.items()):
            print(f"{name}\n    {query.summary}")
            if query.defaults:
                print(f"    params: {json.dumps(query.defaults, default=str)}")
        return 0

    with open_backend(settings) as backend:
        if args.command == "migrate":
            ran = migrate(backend, MIGRATIONS_DIR)
            for migration in ran:
                print(f"applied {migration.version} {migration.name} ({migration.path.name})")
            if not ran:
                print("nothing to apply")
            return 0

        if args.command == "status":
            for migration, state in status(backend, MIGRATIONS_DIR):
                print(f"{state:>8}  {migration.version}  {migration.name}")
            return 0

        if args.command == "ingest":
            counts = ingest_all(backend, DATA_DIR)
            for label, count in counts.items():
                print(f"{count:>6}  {label}")
            return 0

        if args.command == "run":
            params = _parse_params(args.params)
            query = QUERIES[args.name]
            rows = query.run(backend, **params)
            if args.json:
                print(json.dumps(rows, indent=2, default=str))
            else:
                _print_rows(rows)
            return 0

    return 1


def _parse_params(tokens: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            raise SystemExit(f"expected --name value, got {token!r}")
        if index + 1 >= len(tokens):
            raise SystemExit(f"missing value for {token}")
        params[token[2:].replace("-", "_")] = _coerce(tokens[index + 1])
        index += 2
    return params


if __name__ == "__main__":
    sys.exit(main())
