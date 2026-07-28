"""Ingest correctness and the invariants from schema/model.md.

Idempotence is the headline test. A loader that duplicates on the second run is the
most common defect in graph pipelines, it never shows up in a single-run smoke test,
and it is invisible in the output until some sum is quietly twice what it should be.
"""

from __future__ import annotations

from gerdgraph.backend import Backend
from gerdgraph.config import DATA_DIR
from gerdgraph.ingest import ingest_all


def _counts(backend: Backend) -> dict[str, int]:
    return {
        "customers": backend.run("MATCH (c:Customer) RETURN count(*) AS n")[0]["n"],
        "products": backend.run("MATCH (p:Product) RETURN count(*) AS n")[0]["n"],
        "orders": backend.run("MATCH (o:SalesOrder) RETURN count(*) AS n")[0]["n"],
        "suppliers": backend.run("MATCH (s:Supplier) RETURN count(*) AS n")[0]["n"],
        "categories": backend.run("MATCH (c:Category) RETURN count(*) AS n")[0]["n"],
        "placed": backend.run("MATCH ()-[r:PLACED]->() RETURN count(r) AS n")[0]["n"],
        "lines": backend.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) AS n")[0]["n"],
        "sourcing": backend.run("MATCH ()-[r:SUPPLIED_BY]->() RETURN count(r) AS n")[0]["n"],
    }


def test_loads_every_row(graph: Backend, csv_data: dict[str, list[dict[str, str]]]) -> None:
    counts = _counts(graph)
    assert counts["customers"] == len(csv_data["customers"])
    assert counts["products"] == len(csv_data["products"])
    assert counts["orders"] == len(csv_data["orders"])
    assert counts["suppliers"] == len(csv_data["suppliers"])
    assert counts["lines"] == len(csv_data["order_lines"])
    assert counts["placed"] == len(csv_data["orders"])
    # P008 is not sourced yet, so one product has no SUPPLIED_BY edge.
    assert counts["sourcing"] == sum(1 for p in csv_data["products"] if p["supplier_id"])
    assert counts["categories"] == len({p["category"] for p in csv_data["products"]})


def test_ingest_is_idempotent(graph: Backend) -> None:
    before = _counts(graph)
    ingest_all(graph, DATA_DIR)
    ingest_all(graph, DATA_DIR)
    assert _counts(graph) == before


def test_properties_survive_reingest(graph: Backend) -> None:
    ingest_all(graph, DATA_DIR)
    row = graph.run("MATCH (p:Product {sku: 'P007'}) RETURN p.name AS name, p.hazard_class AS hz")
    assert row == [{"name": "Sika PU constructielijm", "hz": "flammable"}]


def test_line_properties_are_typed(graph: Backend) -> None:
    # CSV gives you strings. If qty lands in the graph as "40" instead of 40, every
    # sum() silently becomes a string concatenation or an error, depending on engine.
    row = graph.run(
        """MATCH (:SalesOrder {id: 'O1001'})-[line:CONTAINS]->(:Product {sku: 'P001'})
           RETURN line.qty AS qty, line.unit_price AS unit_price"""
    )[0]
    assert isinstance(row["qty"], int) and row["qty"] == 40
    assert isinstance(row["unit_price"], float) and row["unit_price"] == 8.50


# --- invariants from schema/model.md -------------------------------------------


def test_invariant_orders_have_exactly_one_customer(graph: Backend) -> None:
    rows = graph.run(
        """MATCH (o:SalesOrder)
           OPTIONAL MATCH (c:Customer)-[:PLACED]->(o)
           WITH o, count(c) AS owners
           WHERE owners <> 1
           RETURN o.id AS order_id, owners"""
    )
    assert rows == []


def test_invariant_orders_have_at_least_one_line(graph: Backend) -> None:
    rows = graph.run(
        """MATCH (o:SalesOrder)
           WHERE NOT EXISTS { MATCH (o)-[:CONTAINS]->(:Product) }
           RETURN o.id AS order_id"""
    )
    assert rows == []


def test_invariant_line_amounts_are_sane(graph: Backend) -> None:
    rows = graph.run(
        """MATCH (o:SalesOrder)-[line:CONTAINS]->(p:Product)
           WHERE line.qty <= 0 OR line.unit_price < 0
           RETURN o.id AS order_id, p.sku AS sku"""
    )
    assert rows == []


def test_invariant_products_have_at_most_one_supplier(graph: Backend) -> None:
    rows = graph.run(
        """MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier)
           WITH p, count(s) AS suppliers
           WHERE suppliers > 1
           RETURN p.sku AS sku, suppliers"""
    )
    assert rows == []
