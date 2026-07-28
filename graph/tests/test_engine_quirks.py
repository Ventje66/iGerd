"""Engine behaviour that is not in any dialect table, found by running the code.

Nothing here is about our schema. It is about the gap between Cypher-the-language
and Cypher-the-thing-this-build-actually-does, which you only ever close by
executing queries against the engine you deploy.

Each test pins a fact so that an upgrade tells you when the fact changes, instead of
a dashboard telling you six weeks later.
"""

from __future__ import annotations

import os
import re

import pytest

from gerdgraph.backend import Backend
from gerdgraph.queries import QUERIES


def test_backend_is_the_one_that_was_asked_for(graph: Backend) -> None:
    """The suite must fail, not pass, if it is talking to the wrong engine.

    Without this, a typo'd or dropped GRAPH_BACKEND in CI means the "neo4j" job
    quietly runs on the embedded engine and reports green — a passing check that
    proves nothing, which is worse than a failing one. The dialect is asserted
    rather than assumed for the same reason every aggregate here is checked against
    a reference: a result you did not verify is not a result.
    """
    requested = os.environ.get("GRAPH_BACKEND", "kuzu")
    assert graph.dialect == requested, (
        f"GRAPH_BACKEND={requested!r} but the tests are running against "
        f"{graph.dialect!r}"
    )


MIXED_AGGREGATE = """
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
RETURN c.id AS customer_id,
       count(DISTINCT o) AS orders,
       sum(line.qty * line.unit_price) AS revenue
ORDER BY customer_id
"""

REORDERED_AGGREGATE = """
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
RETURN c.id AS customer_id,
       sum(line.qty * line.unit_price) AS revenue,
       count(DISTINCT o) AS orders
ORDER BY customer_id
"""


def test_distinct_aggregate_poisons_later_aggregates_on_kuzu(graph: Backend) -> None:
    """Kuzu 0.11: a DISTINCT aggregate nulls plain aggregates that follow it.

    The same query with the two RETURN columns swapped gives the right answer. A
    query whose result depends on column order is a bug in the engine, but it is
    our outage — so the shipped queries do not rely on either ordering.

    If this test starts failing, Kuzu fixed it: delete the workaround note in
    queries.py and this test with it.
    """
    if graph.dialect != "kuzu":
        pytest.skip("quirk is specific to Kuzu")

    poisoned = graph.run(MIXED_AGGREGATE)
    reordered = graph.run(REORDERED_AGGREGATE)

    assert all(row["revenue"] is None for row in poisoned)
    assert all(row["revenue"] is not None for row in reordered)
    assert [row["orders"] for row in poisoned] == [row["orders"] for row in reordered]


@pytest.mark.parametrize("name", sorted(QUERIES))
def test_shipped_queries_avoid_the_mixed_aggregate_shape(name: str) -> None:
    """Static guard: never mix a DISTINCT aggregate with a plain one in one clause.

    Enforced rather than remembered, because the failure is a silent NULL and the
    correct-looking version is the one a model reaches for first.
    """
    for clause in re.split(r"\b(?:WITH|RETURN)\b", QUERIES[name].cypher)[1:]:
        clause = clause.split("ORDER BY")[0]
        has_distinct_aggregate = re.search(r"\b(count|sum|collect)\s*\(\s*DISTINCT", clause, re.I)
        has_plain_aggregate = re.search(
            r"\b(count|sum|avg|min|max)\s*\(\s*(?!DISTINCT)", clause, re.I
        )
        assert not (has_distinct_aggregate and has_plain_aggregate), (
            f"{name} mixes DISTINCT and plain aggregates in one clause; "
            "aggregate by grain in a WITH instead"
        )


def test_ordering_is_total(graph: Backend) -> None:
    """Ties broken explicitly, or 'the top 3 customers' changes between runs.

    Every ORDER BY in the library ends in a unique-ish column for this reason.
    """
    first = QUERIES["revenue_by_customer"].run(graph, limit=100)
    second = QUERIES["revenue_by_customer"].run(graph, limit=100)
    assert first == second


def test_missing_optional_edge_yields_null_not_a_dropped_row(graph: Backend) -> None:
    """OPTIONAL MATCH keeps P008; a plain MATCH would silently drop it.

    The dropped-row version is indistinguishable from a correct answer unless you
    already know the count you expect.
    """
    optional = graph.run(
        """MATCH (p:Product)
           OPTIONAL MATCH (p)-[:SUPPLIED_BY]->(s:Supplier)
           RETURN p.sku AS sku, s.name AS supplier
           ORDER BY sku"""
    )
    required = graph.run(
        """MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier)
           RETURN p.sku AS sku, s.name AS supplier
           ORDER BY sku"""
    )

    assert len(optional) == len(required) + 1
    assert [row for row in optional if row["supplier"] is None] == [
        {"sku": "P008", "supplier": None}
    ]
