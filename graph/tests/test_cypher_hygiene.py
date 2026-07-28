"""Static checks on the Cypher in this repo.

Rules a reviewer would have to remember, enforced instead. All of them are things a
model will do if you do not stop it, and none of them fail a functional test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from gerdgraph import ingest, queries
from gerdgraph.config import MIGRATIONS_DIR, MODEL_DOC, PROJECT_ROOT
from gerdgraph.queries import QUERIES

SOURCE_DIR = PROJECT_ROOT / "src" / "gerdgraph"

# ORDER, MATCH, RETURN and friends as node labels are a parse error on at least one
# engine. Kuzu rejects `row.order` outright; Neo4j accepts it and lets the trap sit.
RESERVED_WORDS = {
    "order", "match", "return", "where", "create", "merge", "delete", "set",
    "with", "unwind", "limit", "skip", "union", "call", "yield", "and", "or", "not",
}

ALL_CYPHER = {
    **{f"queries.{name}": query.cypher for name, query in QUERIES.items()},
    **{
        f"ingest.{name}": value
        for name, value in vars(ingest).items()
        if name.isupper() and isinstance(value, str) and "MERGE" in value
    },
}


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.rglob("*.cypher"))


@pytest.mark.parametrize("name", sorted(ALL_CYPHER))
def test_no_string_interpolation_in_cypher(name: str) -> None:
    """Parameters only. An f-string in a query is an injection and a plan-cache miss."""
    cypher = ALL_CYPHER[name]
    assert "{}" not in cypher
    assert not re.search(r"%[sd]", cypher)
    # ${...} is not Cypher; a stray one means someone templated the string.
    assert not re.search(r"\$\{", cypher)


def test_python_sources_never_build_cypher_by_formatting() -> None:
    """Covers tests as well as src: fixtures write Cypher too, and a fixture that
    interpolates is the one that quietly stops testing what you think it tests."""
    offenders = []
    for directory in (SOURCE_DIR, Path(__file__).parent):
        for path in directory.rglob("*.py"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip().startswith("#"):
                    continue
                if re.search(r"f['\"].*\b(MATCH|MERGE|CREATE|RETURN|WHERE)\b", line):
                    # Neo4j cannot parameterise constraint or index names in DROP,
                    # so the teardown fixture is the one legitimate exception.
                    if "DROP" in line:
                        continue
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}")
    assert offenders == [], f"f-string Cypher found: {offenders}"


@pytest.mark.parametrize("name", sorted(ALL_CYPHER))
def test_no_reserved_words_as_identifiers(name: str) -> None:
    cypher = ALL_CYPHER[name]
    # Property access such as `row.order` is the form that actually breaks.
    for match in re.finditer(r"\.(\w+)", cypher):
        assert match.group(1).lower() not in RESERVED_WORDS, (
            f"{name} uses reserved word {match.group(1)!r} as a property name"
        )


@pytest.mark.parametrize("name", sorted(ALL_CYPHER))
def test_relationships_are_directed(name: str) -> None:
    """`(a)-[:R]-(b)` traverses both ways and doubles rows in an aggregate.

    Undirected matching is occasionally what you want; it is never what you want by
    accident, so it has to be argued for rather than typed by habit.
    """
    cypher = ALL_CYPHER[name]
    undirected = re.findall(r"\)-\[[^\]]*\]-\(", cypher)
    assert undirected == [], f"{name} has undirected patterns: {undirected}"


@pytest.mark.parametrize("name", sorted(ALL_CYPHER))
def test_merge_targets_a_single_key_property(name: str) -> None:
    """MERGE on {key} then SET. MERGE on {key, name, ...} duplicates on any change."""
    cypher = ALL_CYPHER[name]
    for pattern in re.findall(r"MERGE\s*\(\s*\w*\s*:\s*\w+\s*\{([^}]*)\}", cypher):
        assert pattern.count(":") <= 1, (
            f"{name} MERGEs on multiple properties ({{{pattern.strip()}}}); "
            "merge on the key and SET the rest"
        )


def test_every_query_has_a_summary_and_a_name() -> None:
    for name, query in QUERIES.items():
        assert query.name == name
        assert query.summary.strip(), f"{name} has no summary"


def test_every_query_is_referenced_by_a_test() -> None:
    """A query nobody asserts on is a query nobody can safely let a model rewrite."""
    test_source = "\n".join(
        path.read_text(encoding="utf-8") for path in Path(__file__).parent.glob("test_*.py")
    )
    untested = [name for name in QUERIES if f'"{name}"' not in test_source]
    assert untested == [], f"queries with no test: {untested}"


def test_migrations_have_no_destructive_statements() -> None:
    """DROP / DETACH DELETE in a migration is how a rerun eats production."""
    forbidden = re.compile(r"\b(DROP\s+(TABLE|CONSTRAINT|INDEX)|DETACH\s+DELETE)\b", re.I)
    offenders = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in _migration_files()
        if forbidden.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"destructive migrations: {offenders}"


def test_model_doc_mentions_every_label_and_relationship() -> None:
    """The doc you paste into a model's context has to describe the real graph."""
    doc = MODEL_DOC.read_text(encoding="utf-8")
    labels = {"Customer", "SalesOrder", "Product", "Supplier", "Category"}
    relationships = {"PLACED", "CONTAINS", "SUPPLIED_BY", "IN_CATEGORY"}
    missing = [token for token in labels | relationships if token not in doc]
    assert missing == [], f"schema/model.md does not document: {missing}"


def test_model_doc_covers_every_queried_label() -> None:
    doc = MODEL_DOC.read_text(encoding="utf-8")
    used = set()
    for cypher in ALL_CYPHER.values():
        used.update(re.findall(r":([A-Z]\w+)", cypher))
    undocumented = sorted(token for token in used if token not in doc)
    assert undocumented == [], f"used in Cypher but not in model.md: {undocumented}"
