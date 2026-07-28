"""Proof that the fan-out bugs are real, and that the shipped queries avoid them.

Both broken queries below are the kind a competent model produces on the first try
from a correct schema description. They parse, they run, they return plausible
numbers, and they are wrong. Nothing about reading them tells you that — only
running them next to a reference does.

Keeping the wrong versions executable is deliberate. If someone "simplifies"
`revenue_by_customer` back into the broken shape, these tests fail immediately.
"""

from __future__ import annotations

import pytest

import reference
from gerdgraph.backend import Backend
from gerdgraph.queries import BROKEN_EXAMPLES, QUERIES

TOLERANCE = 0.01


def test_bare_count_inflates_order_counts(graph: Backend, csv_data) -> None:
    """count(o) after a CONTAINS hop counts lines, not orders."""
    expected_orders = reference.orders_by_customer(csv_data)

    broken = {
        row["customer_id"]: row["orders"]
        for row in graph.run(BROKEN_EXAMPLES["revenue_by_customer_fanout"])
    }
    correct = {
        row["customer_id"]: row["orders"]
        for row in QUERIES["revenue_by_customer"].run(graph, limit=100)
    }

    assert correct == expected_orders
    assert broken != expected_orders

    # Concretely: C001 placed 3 orders holding 7 lines between them.
    assert correct["C001"] == 3
    assert broken["C001"] == 7


def test_bare_count_leaves_revenue_correct(graph: Backend, csv_data) -> None:
    """The subtle part: the same broken query gets the *money* right.

    One wrong column beside several right ones is why this survives review.
    """
    expected = reference.revenue_by_customer(csv_data)
    for row in graph.run(BROKEN_EXAMPLES["revenue_by_customer_fanout"]):
        assert row["revenue"] == pytest.approx(expected[row["customer_id"]], abs=TOLERANCE)


def test_two_branches_in_one_match_inflate_revenue(graph: Backend, csv_data) -> None:
    """A second one-to-many branch multiplies the first branch's rows."""
    expected = reference.revenue_by_customer(csv_data)
    names = {c["name"]: c["id"] for c in csv_data["customers"]}

    broken = graph.run(BROKEN_EXAMPLES["revenue_with_categories_fanout"])
    correct = QUERIES["customer_revenue_with_categories"].run(graph)

    for row in correct:
        assert row["revenue"] == pytest.approx(expected[names[row["customer"]]], abs=TOLERANCE)

    inflated = [
        row
        for row in broken
        if row["revenue"] > expected[names[row["customer"]]] + TOLERANCE
    ]
    assert inflated, "expected the two-branch query to overcount revenue"

    # The inflation factor is the number of category rows the second branch adds,
    # so the error scales with the data. It is not a rounding difference.
    worst = max(inflated, key=lambda row: row["revenue"] / expected[names[row["customer"]]])
    assert worst["revenue"] / expected[names[worst["customer"]]] >= 2.0


def test_distinct_hides_the_duplication_it_does_not_fix_it(graph: Backend) -> None:
    """count(DISTINCT ...) in the broken query looks right while the sum is wrong.

    This is why "add DISTINCT until it looks sane" is not a fix: DISTINCT cleans the
    column you are staring at and leaves the one you are billing on.
    """
    broken = {row["customer"]: row for row in graph.run(
        BROKEN_EXAMPLES["revenue_with_categories_fanout"]
    )}
    correct = {row["customer"]: row for row in
               QUERIES["customer_revenue_with_categories"].run(graph)}

    assert set(broken) == set(correct)
    assert all(broken[name]["categories"] == correct[name]["categories"] for name in broken)
    assert any(broken[name]["revenue"] != correct[name]["revenue"] for name in broken)
