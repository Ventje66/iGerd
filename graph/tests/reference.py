"""A second, independent implementation of the aggregates — plain Python over CSVs.

Asserting Cypher against hand-written constants tells you the query does what it did
yesterday. Asserting it against a naive implementation of the *definition* tells you
it does what you meant, and it keeps telling you that when the fixture data changes.

Deliberately dumb: dicts and loops, no graph concepts. When the Cypher and this file
disagree, they disagree because one of them mis-joined, and that is exactly the class
of bug that reads fine in review.
"""

from __future__ import annotations

from collections import defaultdict


def _line_amounts(csv_data: dict[str, list[dict[str, str]]]) -> list[tuple[str, str, float]]:
    """(order_id, sku, amount) for every order line."""
    return [
        (line["order_id"], line["sku"], int(line["qty"]) * float(line["unit_price"]))
        for line in csv_data["order_lines"]
    ]


def revenue_by_customer(csv_data: dict[str, list[dict[str, str]]]) -> dict[str, float]:
    owner = {o["id"]: o["customer_id"] for o in csv_data["orders"]}
    totals: dict[str, float] = defaultdict(float)
    for order_id, _sku, amount in _line_amounts(csv_data):
        totals[owner[order_id]] += amount
    return dict(totals)


def orders_by_customer(csv_data: dict[str, list[dict[str, str]]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for order in csv_data["orders"]:
        counts[order["customer_id"]] += 1
    return dict(counts)


def revenue_by_category(csv_data: dict[str, list[dict[str, str]]]) -> dict[str, float]:
    category = {p["sku"]: p["category"] for p in csv_data["products"]}
    totals: dict[str, float] = defaultdict(float)
    for _order_id, sku, amount in _line_amounts(csv_data):
        totals[category[sku]] += amount
    return dict(totals)


def revenue_by_supplier(csv_data: dict[str, list[dict[str, str]]]) -> dict[str, float]:
    supplier = {p["sku"]: p["supplier_id"] for p in csv_data["products"]}
    totals: dict[str, float] = defaultdict(float)
    for _order_id, sku, amount in _line_amounts(csv_data):
        if supplier[sku]:
            totals[supplier[sku]] += amount
    return dict(totals)


def revenue_at_risk_by_customer(
    csv_data: dict[str, list[dict[str, str]]], supplier_id: str
) -> dict[str, float]:
    supplier = {p["sku"]: p["supplier_id"] for p in csv_data["products"]}
    owner = {o["id"]: o["customer_id"] for o in csv_data["orders"]}
    totals: dict[str, float] = defaultdict(float)
    for order_id, sku, amount in _line_amounts(csv_data):
        if supplier[sku] == supplier_id:
            totals[owner[order_id]] += amount
    return dict(totals)


def pairs_bought_together(csv_data: dict[str, list[dict[str, str]]]) -> dict[tuple[str, str], int]:
    by_order: dict[str, set[str]] = defaultdict(set)
    for line in csv_data["order_lines"]:
        by_order[line["order_id"]].add(line["sku"])

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for skus in by_order.values():
        ordered = sorted(skus)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                counts[(a, b)] += 1
    return dict(counts)


def shared_product_counts(
    csv_data: dict[str, list[dict[str, str]]], customer_id: str
) -> dict[str, int]:
    owner = {o["id"]: o["customer_id"] for o in csv_data["orders"]}
    bought: dict[str, set[str]] = defaultdict(set)
    for line in csv_data["order_lines"]:
        bought[owner[line["order_id"]]].add(line["sku"])

    mine = bought.get(customer_id, set())
    return {
        peer: len(mine & skus)
        for peer, skus in bought.items()
        if peer != customer_id and mine & skus
    }
