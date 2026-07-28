"""The query library.

Every query the application runs lives here, named, parameterised, and covered by a
test in ``tests/test_queries.py``. Nothing builds Cypher by string formatting —
``tests/test_cypher_hygiene.py`` enforces that mechanically.

Why a library instead of inline strings: a named query with a test is a thing you can
regenerate. When you ask a model to rewrite ``revenue_by_customer``, the test decides
whether the rewrite was an improvement or a regression, and you never have to read
the new Cypher hoping to spot a fan-out by eye.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .backend import Backend, Row


@dataclass(frozen=True)
class Query:
    name: str
    summary: str
    cypher: str
    defaults: dict[str, object] = field(default_factory=dict)

    def run(self, backend: Backend, **params: object) -> list[Row]:
        return backend.run(self.cypher, {**self.defaults, **params})


QUERIES: dict[str, Query] = {}


def _register(query: Query) -> Query:
    QUERIES[query.name] = query
    return query


revenue_by_customer = _register(
    Query(
        name="revenue_by_customer",
        summary="Top customers by revenue, with a correct order count.",
        # Aggregate at the grain you have, then roll up. The MATCH yields one row
        # per order *line*, so a bare count(o) reports 7 orders for a customer who
        # placed 3 (see BROKEN_EXAMPLES). Collapsing to one row per (customer,
        # order) in the WITH makes count(o) mean what it says.
        #
        # The obvious alternative — count(DISTINCT o) straight in the RETURN — is
        # correct Cypher but hits an engine bug on Kuzu 0.11: a DISTINCT aggregate
        # followed by a plain one nulls the later column, and swapping the column
        # order changes the answer. Aggregating by grain is portable and clearer
        # about intent. See docs/engine-notes.md.
        cypher="""
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
WITH c, o, sum(line.qty * line.unit_price) AS order_total
RETURN c.id AS customer_id,
       c.name AS customer,
       count(o) AS orders,
       round(sum(order_total), 2) AS revenue
ORDER BY revenue DESC, customer
LIMIT $limit
""",
        defaults={"limit": 10},
    )
)


customer_revenue_with_categories = _register(
    Query(
        name="customer_revenue_with_categories",
        summary="Revenue per customer alongside the categories they buy from.",
        # Two one-to-many branches, so they must not share a MATCH. Aggregate the
        # money first, carry the scalar through WITH, then join the second branch.
        cypher="""
MATCH (c:Customer)-[:PLACED]->(:SalesOrder)-[line:CONTAINS]->(:Product)
WITH c, round(sum(line.qty * line.unit_price), 2) AS revenue
MATCH (c)-[:PLACED]->(:SalesOrder)-[:CONTAINS]->(:Product)-[:IN_CATEGORY]->(cat:Category)
RETURN c.name AS customer,
       revenue,
       count(DISTINCT cat.name) AS categories
ORDER BY revenue DESC, customer
""",
    )
)


revenue_by_category = _register(
    Query(
        name="revenue_by_category",
        summary="Revenue and line count per product category.",
        cypher="""
MATCH (:SalesOrder)-[line:CONTAINS]->(:Product)-[:IN_CATEGORY]->(cat:Category)
RETURN cat.name AS category,
       count(line) AS lines,
       round(sum(line.qty * line.unit_price), 2) AS revenue
ORDER BY revenue DESC, category
""",
    )
)


frequently_bought_together = _register(
    Query(
        name="frequently_bought_together",
        summary="Product pairs appearing in the same order.",
        # a.sku < b.sku does two jobs: it drops the (a, a) self-pairs and it keeps
        # each unordered pair once instead of twice.
        cypher="""
MATCH (a:Product)<-[:CONTAINS]-(o:SalesOrder)-[:CONTAINS]->(b:Product)
WHERE a.sku < b.sku
RETURN a.name AS product_a,
       b.name AS product_b,
       count(DISTINCT o) AS orders_together
ORDER BY orders_together DESC, product_a, product_b
LIMIT $limit
""",
        defaults={"limit": 10},
    )
)


supplier_revenue_exposure = _register(
    Query(
        name="supplier_revenue_exposure",
        summary="Revenue depending on each supplier — the reason this is a graph.",
        cypher="""
MATCH (s:Supplier)<-[:SUPPLIED_BY]-(:Product)<-[line:CONTAINS]-(:SalesOrder)
RETURN s.id AS supplier_id,
       s.name AS supplier,
       round(sum(line.qty * line.unit_price), 2) AS revenue
ORDER BY revenue DESC, supplier
""",
    )
)


customers_exposed_to_supplier = _register(
    Query(
        name="customers_exposed_to_supplier",
        summary="If one supplier stops shipping, which customers are affected.",
        # Four hops from supplier to customer. This is the query that would be a
        # four-way join with two junction tables in SQL, and it is the whole
        # argument for keeping this data in a graph.
        cypher="""
MATCH (s:Supplier {id: $supplier_id})<-[:SUPPLIED_BY]-(p:Product)
      <-[line:CONTAINS]-(:SalesOrder)<-[:PLACED]-(c:Customer)
WITH c, p, sum(line.qty * line.unit_price) AS product_revenue
RETURN c.id AS customer_id,
       c.name AS customer,
       count(p) AS products,
       round(sum(product_revenue), 2) AS revenue_at_risk
ORDER BY revenue_at_risk DESC, customer
""",
        defaults={"supplier_id": "S01"},
    )
)


similar_customers = _register(
    Query(
        name="similar_customers",
        summary="Customers who buy the same products as a given customer.",
        cypher="""
MATCH (me:Customer {id: $customer_id})-[:PLACED]->(:SalesOrder)-[:CONTAINS]->(p:Product)
      <-[:CONTAINS]-(:SalesOrder)<-[:PLACED]-(peer:Customer)
WHERE peer.id <> $customer_id
RETURN peer.id AS customer_id,
       peer.name AS customer,
       count(DISTINCT p) AS shared_products
ORDER BY shared_products DESC, customer
LIMIT $limit
""",
        defaults={"customer_id": "C001", "limit": 5},
    )
)


orders_in_window = _register(
    Query(
        name="orders_in_window",
        summary="Orders placed in a date window, with their line totals.",
        # placed_on is an ISO-8601 string, so lexicographic comparison is date
        # comparison. That holds for 'YYYY-MM-DD' and stops holding the moment
        # someone writes a 'DD/MM/YYYY'; the ingest is what keeps the promise.
        cypher="""
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
WHERE o.placed_on >= $from_date AND o.placed_on <= $to_date
RETURN o.id AS order_id,
       o.placed_on AS placed_on,
       c.name AS customer,
       count(line) AS lines,
       round(sum(line.qty * line.unit_price), 2) AS order_total
ORDER BY placed_on, order_id
""",
        defaults={"from_date": "2026-01-01", "to_date": "2026-12-31"},
    )
)


unsourced_products = _register(
    Query(
        name="unsourced_products",
        summary="Products with no supplier — invariant 5 in schema/model.md.",
        cypher="""
MATCH (p:Product)
WHERE NOT EXISTS { MATCH (p)-[:SUPPLIED_BY]->(:Supplier) }
RETURN p.sku AS sku, p.name AS name
ORDER BY sku
""",
    )
)


longest_lead_times = _register(
    Query(
        name="longest_lead_times",
        summary="Sourcing risk: which sold products take longest to restock.",
        cypher="""
MATCH (p:Product)-[r:SUPPLIED_BY]->(s:Supplier)
RETURN p.sku AS sku,
       p.name AS product,
       s.name AS supplier,
       r.lead_time_days AS lead_time_days
ORDER BY lead_time_days DESC, sku
LIMIT $limit
""",
        defaults={"limit": 5},
    )
)


# --------------------------------------------------------------------------------
# Executable warnings.
#
# These are wrong on purpose. tests/test_fanout.py runs them next to their correct
# counterparts and asserts that the answers differ, so the failure mode stays
# demonstrated instead of merely described — and so nobody "fixes" the correct query
# into one of these.
# --------------------------------------------------------------------------------

BROKEN_EXAMPLES: dict[str, str] = {
    # count(o) counts matched rows, and the MATCH yields one row per order line.
    # Revenue is right; the order count is inflated by lines-per-order.
    "revenue_by_customer_fanout": """
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
RETURN c.id AS customer_id,
       count(o) AS orders,
       round(sum(line.qty * line.unit_price), 2) AS revenue
ORDER BY customer_id
""",
    # Two one-to-many branches in one MATCH: every line row is repeated once per
    # category row, so the money is multiplied. DISTINCT on the collect hides the
    # duplication in the category column while leaving it in the sum.
    "revenue_with_categories_fanout": """
MATCH (c:Customer)-[:PLACED]->(:SalesOrder)-[line:CONTAINS]->(:Product)
MATCH (c)-[:PLACED]->(:SalesOrder)-[:CONTAINS]->(:Product)-[:IN_CATEGORY]->(cat:Category)
RETURN c.name AS customer,
       round(sum(line.qty * line.unit_price), 2) AS revenue,
       count(DISTINCT cat.name) AS categories
ORDER BY customer
""",
}
