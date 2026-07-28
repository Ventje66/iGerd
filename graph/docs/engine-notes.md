# Engine notes

Facts about the engines that are not in the Cypher documentation, found by running
queries and reading results. Each one is pinned by a test, so an upgrade reports the
change instead of a dashboard doing it later.

## Kùzu 0.11.3 — a DISTINCT aggregate nulls plain aggregates after it

```cypher
-- revenue comes back NULL for every row
RETURN c.id, count(DISTINCT o) AS orders, sum(line.qty * line.unit_price) AS revenue

-- swap the two columns and revenue is correct
RETURN c.id, sum(line.qty * line.unit_price) AS revenue, count(DISTINCT o) AS orders
```

A result that depends on the order of columns in the `RETURN`. Both forms are valid
Cypher and both are correct on Neo4j.

**What we do instead:** aggregate at the grain we have, then roll up.

```cypher
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
WITH c, o, sum(line.qty * line.unit_price) AS order_total
RETURN c.id AS customer_id, count(o) AS orders, round(sum(order_total), 2) AS revenue
```

One row per `(customer, order)` after the `WITH`, so `count(o)` needs no `DISTINCT` at
all. Portable, and it says what it means. `tests/test_engine_quirks.py` pins the
broken behaviour and statically forbids the mixed-aggregate shape everywhere else.

Worth sitting with: this bug produces `NULL`, which is the *good* case. The same
class of engine difference that returns a plausible number instead is the reason the
test suite compares against `tests/reference.py` rather than against golden values
captured from the engine.

## Kùzu — `ORDER` is reserved, and so is anything that looks like a keyword

`MATCH (o:Order)` and `row.order` are both parse errors. Neo4j accepts both, so a
model with Neo4j in its training data will write them, and the failure only appears
on the other engine.

Hence `SalesOrder`, and `row.order_id` rather than `row.order` in the ingest.
`tests/test_cypher_hygiene.py::test_no_reserved_words_as_identifiers` blocks the
whole class.

## Kùzu is schema-first; Neo4j is schema-optional

| | Kùzu | Neo4j |
|---|---|---|
| New label | `CREATE NODE TABLE` | nothing — it exists when you write one |
| New relationship type | `CREATE REL TABLE` with fixed FROM/TO | nothing |
| New property | `ALTER TABLE ... ADD ... DEFAULT` (backfills) | nothing, but no default either — backfill by hand |
| Uniqueness | `PRIMARY KEY`, mandatory | `CREATE CONSTRAINT`, optional |
| Typo in a property name | error | a new property, silently |

The last row is the one that costs money. On Neo4j, `SET p.hazrd_class = 'none'`
succeeds and creates a property nobody reads. Constraints do not catch it; only a
test that reads the value back does.

This asymmetry is why the migrations are written twice rather than generated from a
shared abstraction. `002_category_dimension` is three DDL statements on Kùzu and one
constraint plus a data backfill on Neo4j — the same intent, genuinely different work.

## Kùzu writes a file, not a directory

`kuzu.Database("path/to/db")` creates a *file*. `shutil.rmtree` on it fails, and with
`ignore_errors=True` it fails silently, so the next run reuses a database you thought
you deleted and greets you with `Binder exception: Customer already exists in
catalog`. Use a fresh `tmp_path` per test (which is what the fixtures do).

## Neo4j — schema and data statements cannot share a transaction

A migration file mixing `CREATE CONSTRAINT` with `MATCH ... SET` runs as separate
transactions. A failure part-way leaves the earlier statements applied. Every
migration statement in this repo is therefore individually idempotent
(`IF NOT EXISTS`, `MERGE`, or a `WHERE`-guarded `SET`), and the runner records the
version only after the whole file succeeds — so a partial failure re-runs cleanly.

Kùzu allows an explicit `BEGIN TRANSACTION` around the whole script, which the
backend uses. Same migrations, different atomicity guarantees. Do not assume the
stronger one.
