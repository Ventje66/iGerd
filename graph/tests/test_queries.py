"""Every query in the library, checked against an independent implementation.

This is the file that lets you hand Cypher to a model and take the result seriously.
"""

from __future__ import annotations

import pytest

import reference
from gerdgraph.backend import Backend
from gerdgraph.queries import QUERIES

TOLERANCE = 0.01


def test_every_registered_query_runs(graph: Backend) -> None:
    # Cheap, and it catches the failure that matters most on a schema-first engine:
    # a query naming a label or relationship type that does not exist.
    for name, query in QUERIES.items():
        rows = query.run(graph)
        assert isinstance(rows, list), f"{name} returned {type(rows).__name__}, not rows"


def test_revenue_by_customer_matches_reference(graph: Backend, csv_data) -> None:
    expected_revenue = reference.revenue_by_customer(csv_data)
    expected_orders = reference.orders_by_customer(csv_data)

    rows = QUERIES["revenue_by_customer"].run(graph, limit=100)

    assert len(rows) == len(expected_revenue)
    for row in rows:
        customer_id = row["customer_id"]
        assert row["revenue"] == pytest.approx(expected_revenue[customer_id], abs=TOLERANCE)
        assert row["orders"] == expected_orders[customer_id]


def test_revenue_by_customer_is_sorted_and_limited(graph: Backend) -> None:
    rows = QUERIES["revenue_by_customer"].run(graph, limit=3)
    assert len(rows) == 3
    assert [row["revenue"] for row in rows] == sorted(
        (row["revenue"] for row in rows), reverse=True
    )


def test_revenue_by_category_matches_reference(graph: Backend, csv_data) -> None:
    expected = reference.revenue_by_category(csv_data)
    rows = QUERIES["revenue_by_category"].run(graph)

    assert {row["category"] for row in rows} == set(expected)
    for row in rows:
        assert row["revenue"] == pytest.approx(expected[row["category"]], abs=TOLERANCE)

    assert sum(row["lines"] for row in rows) == len(csv_data["order_lines"])


def test_category_revenue_sums_to_total(graph: Backend, csv_data) -> None:
    # Partition check. Every line belongs to exactly one category, so the parts must
    # add up to the whole — the cheapest possible test for a silent fan-out.
    total = sum(reference.revenue_by_customer(csv_data).values())
    rows = QUERIES["revenue_by_category"].run(graph)
    assert sum(row["revenue"] for row in rows) == pytest.approx(total, abs=TOLERANCE)


def test_supplier_exposure_matches_reference(graph: Backend, csv_data) -> None:
    expected = reference.revenue_by_supplier(csv_data)
    rows = QUERIES["supplier_revenue_exposure"].run(graph)

    assert {row["supplier_id"] for row in rows} == set(expected)
    for row in rows:
        assert row["revenue"] == pytest.approx(expected[row["supplier_id"]], abs=TOLERANCE)


def test_supplier_exposure_excludes_unsourced_revenue(graph: Backend, csv_data) -> None:
    # P008 has no supplier, so supplier revenue must come in *under* total revenue.
    # Getting the total here would mean the join invented a supplier edge.
    total = sum(reference.revenue_by_customer(csv_data).values())
    rows = QUERIES["supplier_revenue_exposure"].run(graph)
    assert sum(row["revenue"] for row in rows) < total


@pytest.mark.parametrize("supplier_id", ["S01", "S02", "S03", "S04"])
def test_customers_exposed_to_supplier(graph: Backend, csv_data, supplier_id: str) -> None:
    expected = reference.revenue_at_risk_by_customer(csv_data, supplier_id)
    rows = QUERIES["customers_exposed_to_supplier"].run(graph, supplier_id=supplier_id)

    assert {row["customer_id"] for row in rows} == set(expected)
    for row in rows:
        assert row["revenue_at_risk"] == pytest.approx(
            expected[row["customer_id"]], abs=TOLERANCE
        )


def test_customers_exposed_to_unknown_supplier_is_empty(graph: Backend) -> None:
    assert QUERIES["customers_exposed_to_supplier"].run(graph, supplier_id="NOPE") == []


def test_frequently_bought_together_matches_reference(graph: Backend, csv_data) -> None:
    expected = reference.pairs_bought_together(csv_data)
    names = {p["sku"]: p["name"] for p in csv_data["products"]}
    expected_by_name = {
        (names[a], names[b]): count for (a, b), count in expected.items()
    }

    rows = QUERIES["frequently_bought_together"].run(graph, limit=100)

    assert len(rows) == len(expected_by_name)
    for row in rows:
        key = (row["product_a"], row["product_b"])
        assert key in expected_by_name
        assert row["orders_together"] == expected_by_name[key]


def test_similar_customers_matches_reference(graph: Backend, csv_data) -> None:
    expected = reference.shared_product_counts(csv_data, "C001")
    rows = QUERIES["similar_customers"].run(graph, customer_id="C001", limit=100)

    assert {row["customer_id"] for row in rows} == set(expected)
    for row in rows:
        assert row["shared_products"] == expected[row["customer_id"]]


def test_similar_customers_excludes_self(graph: Backend) -> None:
    rows = QUERIES["similar_customers"].run(graph, customer_id="C001", limit=100)
    assert "C001" not in {row["customer_id"] for row in rows}


def test_orders_in_window_filters(graph: Backend, csv_data) -> None:
    rows = QUERIES["orders_in_window"].run(graph, from_date="2026-02-01", to_date="2026-02-28")
    expected = {
        o["id"] for o in csv_data["orders"] if "2026-02-01" <= o["placed_on"] <= "2026-02-28"
    }
    assert {row["order_id"] for row in rows} == expected


def test_orders_in_window_totals_match_lines(graph: Backend, csv_data) -> None:
    rows = QUERIES["orders_in_window"].run(graph)
    by_order: dict[str, float] = {}
    for line in csv_data["order_lines"]:
        amount = int(line["qty"]) * float(line["unit_price"])
        by_order[line["order_id"]] = by_order.get(line["order_id"], 0.0) + amount

    assert len(rows) == len(by_order)
    for row in rows:
        assert row["order_total"] == pytest.approx(by_order[row["order_id"]], abs=TOLERANCE)


def test_unsourced_products(graph: Backend, csv_data) -> None:
    expected = {p["sku"] for p in csv_data["products"] if not p["supplier_id"]}
    rows = QUERIES["unsourced_products"].run(graph)
    assert {row["sku"] for row in rows} == expected


def test_longest_lead_times_is_ordered(graph: Backend, csv_data) -> None:
    rows = QUERIES["longest_lead_times"].run(graph, limit=100)
    expected = {p["sku"] for p in csv_data["products"] if p["supplier_id"]}
    assert {row["sku"] for row in rows} == expected
    lead_times = [row["lead_time_days"] for row in rows]
    assert lead_times == sorted(lead_times, reverse=True)


def test_customer_revenue_with_categories_matches_reference(graph: Backend, csv_data) -> None:
    expected_revenue = reference.revenue_by_customer(csv_data)
    rows = QUERIES["customer_revenue_with_categories"].run(graph)

    assert len(rows) == len(expected_revenue)
    names = {c["name"]: c["id"] for c in csv_data["customers"]}
    for row in rows:
        customer_id = names[row["customer"]]
        assert row["revenue"] == pytest.approx(expected_revenue[customer_id], abs=TOLERANCE)
        assert row["categories"] >= 1
