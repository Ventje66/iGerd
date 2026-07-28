"""Idempotent, batched loading from CSV.

Three rules are doing all the work here, and all three are things a model will get
wrong if you do not state them:

1. **MERGE on the key alone, then SET the rest.**
   ``MERGE (p:Product {sku: $sku, name: $name})`` matches on the *whole* pattern, so
   the day a product is renamed you get a second node with the same sku. MERGE on
   ``{sku}``, then ``SET`` the mutable properties.

2. **Nodes first, then edges.** An edge MERGE that has to create its endpoints
   creates them without their properties.

3. **UNWIND a parameter list, do not build a statement per row.** One round trip per
   batch instead of per row, one query plan instead of thousands, and no string
   interpolation anywhere near user data.

Re-running ingest on an unchanged file is a no-op. That is what makes it safe to put
in a pipeline that retries.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator, Sequence

from .backend import Backend, Row

BATCH_SIZE = 500


def read_csv(path: Path) -> list[Row]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def batched(rows: Sequence[Row], size: int = BATCH_SIZE) -> Iterator[list[Row]]:
    for start in range(0, len(rows), size):
        yield list(rows[start : start + size])


def _int(value: Any) -> int | None:
    return int(value) if value not in (None, "") else None


def _float(value: Any) -> float | None:
    return float(value) if value not in (None, "") else None


def _load(backend: Backend, cypher: str, rows: Sequence[Row]) -> int:
    """Run one UNWIND-based statement over rows, in batches."""
    for batch in batched(rows):
        backend.run(cypher, {"rows": batch})
    return len(rows)


CUSTOMERS = """
UNWIND $rows AS row
MERGE (c:Customer {id: row.id})
SET c.name = row.name,
    c.segment = row.segment,
    c.country = row.country
"""

SUPPLIERS = """
UNWIND $rows AS row
MERGE (s:Supplier {id: row.id})
SET s.name = row.name,
    s.country = row.country
"""

PRODUCTS = """
UNWIND $rows AS row
MERGE (p:Product {sku: row.sku})
SET p.name = row.name,
    p.unit = row.unit,
    p.hazard_class = row.hazard_class
"""

CATEGORIES = """
UNWIND $rows AS row
MERGE (c:Category {name: row.name})
"""

ORDERS = """
UNWIND $rows AS row
MERGE (o:SalesOrder {id: row.id})
SET o.placed_on = row.placed_on,
    o.channel = row.channel
"""

PLACED = """
UNWIND $rows AS row
MATCH (c:Customer {id: row.customer_id}), (o:SalesOrder {id: row.order_id})
MERGE (c)-[:PLACED]->(o)
"""

IN_CATEGORY = """
UNWIND $rows AS row
MATCH (p:Product {sku: row.sku}), (c:Category {name: row.category})
MERGE (p)-[:IN_CATEGORY]->(c)
"""

SUPPLIED_BY = """
UNWIND $rows AS row
MATCH (p:Product {sku: row.sku}), (s:Supplier {id: row.supplier_id})
MERGE (p)-[r:SUPPLIED_BY]->(s)
SET r.lead_time_days = row.lead_time_days
"""

ORDER_LINES = """
UNWIND $rows AS row
MATCH (o:SalesOrder {id: row.order_id}), (p:Product {sku: row.sku})
MERGE (o)-[line:CONTAINS]->(p)
SET line.qty = row.qty,
    line.unit_price = row.unit_price
"""


def ingest_all(backend: Backend, data_dir: Path) -> dict[str, int]:
    """Load every CSV in ``data_dir`` into the graph. Safe to re-run."""
    customers = read_csv(data_dir / "customers.csv")
    suppliers = read_csv(data_dir / "suppliers.csv")
    products = read_csv(data_dir / "products.csv")
    orders = read_csv(data_dir / "orders.csv")
    lines = read_csv(data_dir / "order_lines.csv")

    categories = [{"name": name} for name in sorted({p["category"] for p in products})]
    product_nodes = [
        {
            "sku": p["sku"],
            "name": p["name"],
            "unit": p["unit"],
            "hazard_class": p["hazard_class"] or "none",
        }
        for p in products
    ]
    # P008 has no supplier yet: filter, do not MATCH on an empty key. A MATCH that
    # finds nothing silently drops the row, which looks identical to success.
    sourcing = [
        {
            "sku": p["sku"],
            "supplier_id": p["supplier_id"],
            "lead_time_days": _int(p["lead_time_days"]),
        }
        for p in products
        if p["supplier_id"]
    ]
    categorisation = [{"sku": p["sku"], "category": p["category"]} for p in products]
    placements = [{"customer_id": o["customer_id"], "order_id": o["id"]} for o in orders]
    order_lines = [
        {
            "order_id": line["order_id"],
            "sku": line["sku"],
            "qty": _int(line["qty"]),
            "unit_price": _float(line["unit_price"]),
        }
        for line in lines
    ]

    return {
        # Nodes first...
        "customers": _load(backend, CUSTOMERS, customers),
        "suppliers": _load(backend, SUPPLIERS, suppliers),
        "categories": _load(backend, CATEGORIES, categories),
        "products": _load(backend, PRODUCTS, product_nodes),
        "orders": _load(backend, ORDERS, orders),
        # ...then edges.
        "placed": _load(backend, PLACED, placements),
        "in_category": _load(backend, IN_CATEGORY, categorisation),
        "supplied_by": _load(backend, SUPPLIED_BY, sourcing),
        "order_lines": _load(backend, ORDER_LINES, order_lines),
    }
