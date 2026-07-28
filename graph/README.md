# Graph engineering with Opus 5

A working scaffold and the method that goes with it. Clone, run it, then point the
same structure at your own graph.

```bash
cd graph
pip install -e ".[dev]"
python -m gerdgraph migrate
python -m gerdgraph ingest
python -m gerdgraph run revenue_by_customer --limit 4
pytest
```

```
customer_id  customer               orders  revenue
-----------  ---------------------  ------  --------
C004         Renovatie De Smet      2       2,706.80
C001         Bouwbedrijf Vermeulen  3       2,578.75
C006         Aannemer Janssens      1       2,410.40
C002         Dakwerken Peeters      2       2,030.00
```

No server required — the default engine is embedded. `docker compose up -d` and
`GRAPH_BACKEND=neo4j` runs the identical code and the identical test suite against
Neo4j.

CI runs both: the suite on Python 3.10–3.12 against the embedded engine, and the
same suite against a real Neo4j service container
([`.github/workflows/graph-tests.yml`](../.github/workflows/graph-tests.yml)). The
scaffold claims to run on two engines, and a claim nobody executes is a guess — the
Neo4j job is there so the portability story is tested rather than asserted.

---

## The actual problem

A model that knows Cypher will write you a query that parses, runs, returns rows
shaped exactly like you asked, and is wrong. Not wrong in a way that throws — wrong
in a way that reports a customer placed 7 orders when they placed 3.

Here is the pair, both from this repo. Same graph, same question.

```cypher
-- what a good model writes first
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
RETURN c.id, count(o) AS orders, sum(line.qty * line.unit_price) AS revenue

-- what is true
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)-[line:CONTAINS]->(:Product)
WITH c, o, sum(line.qty * line.unit_price) AS order_total
RETURN c.id, count(o) AS orders, round(sum(order_total), 2) AS revenue
```

The `MATCH` yields one row per order *line*. `count(o)` counts those rows. Revenue is
correct in both — it is the order count that lies, which is precisely why it ships:
one wrong column next to three right ones, in a result set that looks entirely
reasonable.

You cannot fix this by prompting harder, and you cannot reliably catch it by reading
the Cypher. Both are true of a human writing the same query; the model just produces
more of them per hour. So the work is not "get better Cypher out of the model." It is
**build the thing that tells you which Cypher is wrong**, then let the model write as
much as it wants.

Everything below is that thing.

---

## The loop

```
    schema/model.md ──────► the contract, and the only context the model needs
           │
           ▼
    migrate  ──► versioned, checksummed, idempotent DDL
           │
           ▼
    ingest   ──► batched, idempotent, MERGE-on-key
           │
           ▼
    queries  ──► named, parameterised, in one library
           │
           ▼
    verify   ──► asserted against an independent implementation
```

Each stage exists because a specific thing goes wrong without it.

### 1. Model — one page, and it is the context

[`schema/model.md`](schema/model.md) is the entire context a model needs to write
correct Cypher for this graph. Not the repository, not the CSVs — one page of labels,
relationships, cardinalities, and invariants.

The one section that earns its place:

> **Counting rule.** Revenue always comes from `CONTAINS` edges: `sum(line.qty *
> line.unit_price)`. If a query matches a second one-to-many branch in the same
> `MATCH`, the `CONTAINS` rows are multiplied and the sum silently inflates.
> Aggregate first, join second.

Cardinality is the thing models get wrong, because it is the thing that is not
visible in the data they are looking at. Write down which relationships are one-to-many
and what the fan-out means for aggregates, and a large class of wrong queries stops
being generated. Leave it out and you will re-derive it in every code review.

Keep the doc honest — `test_cypher_hygiene.py` fails if a label used in a query is
missing from it. A stale model doc is worse than none: it produces *confidently* wrong
Cypher.

### 2. Migrate — so the schema has a version

[`src/gerdgraph/migrate.py`](src/gerdgraph/migrate.py). Versioned directories, one
file per dialect, checksummed, recorded in the graph itself as `SchemaMigration`
nodes.

The property that matters most: **editing an applied migration is refused.**

```
MigrationError: migration 002 was modified after it was applied
(recorded 9c1e..., file is 4a77...). Add a new migration instead of editing
an applied one.
```

When you ask a model to change the schema, its instinct is to edit the file that
defines the schema. That is the right instinct for source code and a data-loss bug for
migrations — the file now describes a graph that no existing database has. Making it
an error converts an invisible drift into a message.

### 3. Ingest — so re-running is safe

[`src/gerdgraph/ingest.py`](src/gerdgraph/ingest.py). Three rules, each of which a
model breaks by default:

**MERGE on the key alone, then SET.**

```cypher
MERGE (p:Product {sku: row.sku, name: row.name})   -- duplicates on any rename
MERGE (p:Product {sku: row.sku}) SET p.name = row.name   -- correct
```

`MERGE` matches the whole pattern. Include a mutable property and the day it changes
you get a second node with the same key. `test_cypher_hygiene.py` rejects any `MERGE`
with more than one property in the pattern.

**Nodes before edges.** An edge `MERGE` that has to create its endpoints creates them
without their properties.

**`UNWIND $rows`, never a statement per row.** One round trip and one query plan per
batch instead of per row — and no string formatting anywhere near your data.

Test it by running it twice and asserting the counts did not move. A loader that
duplicates on the second run is the most common defect in graph pipelines, it passes
every single-run smoke test, and it is invisible until some total is quietly double.

### 4. Query — a library, not strings at call sites

[`src/gerdgraph/queries.py`](src/gerdgraph/queries.py). Every query named,
parameterised, with a summary, registered in one dict.

This is what makes model-written Cypher *safe to accept*: a named query with a test is
a thing you can regenerate. Ask for a rewrite of `revenue_by_customer` and the test
decides whether it was an improvement or a regression. You never have to spot a
fan-out by eye, which is good, because you will not.

`test_every_query_is_referenced_by_a_test` fails on any query without one. An
unasserted query is a query nobody can safely let a model touch.

### 5. Verify — against a second implementation, not against yesterday

This is the part people skip, and it is the part that works.

[`tests/reference.py`](tests/reference.py) recomputes every aggregate in plain Python
over the source CSVs — dicts and loops, no graph concepts:

```python
def revenue_by_customer(csv_data):
    owner = {o["id"]: o["customer_id"] for o in csv_data["orders"]}
    totals = defaultdict(float)
    for line in csv_data["order_lines"]:
        totals[owner[line["order_id"]]] += int(line["qty"]) * float(line["unit_price"])
    return dict(totals)
```

Asserting Cypher against golden constants tells you it does what it did yesterday.
Asserting it against an independent implementation of the *definition* tells you it
does what you meant — and keeps telling you when the fixture data changes. A fan-out
cannot survive it, because the naive loop has no joins to get wrong.

Two more checks that cost nothing:

- **Partition checks.** Every line belongs to exactly one category, so category
  revenue must sum to total revenue. One assertion, catches any silent duplication.
- **Strict inequalities.** One product has no supplier, so supplier revenue must come
  in *under* total revenue. Equality would mean the join invented an edge.

---

## The tests are the deliverable

134 of them, all against a real Cypher engine on a temp file, whole suite in a few
seconds. That speed is a design constraint, not a nice-to-have: if the tests needed a
server, you would write three and stop, and then nothing would be checking the Cypher
a model hands you.

| File | What it defends |
|---|---|
| `test_migrate.py` | applied once, in order, loud when repo and database disagree |
| `test_ingest.py` | idempotence, types survive the CSV boundary, model invariants hold |
| `test_queries.py` | every query vs. an independent implementation |
| `test_fanout.py` | the wrong queries, kept executable, proven wrong |
| `test_cypher_hygiene.py` | static rules: no interpolation, no reserved words, MERGE on key, directed edges |
| `test_engine_quirks.py` | engine behaviour found by running, pinned so upgrades report it |

[`test_fanout.py`](tests/test_fanout.py) is the unusual one and the most useful. The
broken queries stay in the repo, executable, in `BROKEN_EXAMPLES`, with tests
asserting they disagree with the reference. So the failure mode stays *demonstrated*
rather than described in a comment nobody reads — and if someone simplifies the
correct query back into the broken shape, the suite says so immediately.

It also pins the subtle part:

```python
def test_distinct_hides_the_duplication_it_does_not_fix_it(graph):
    """count(DISTINCT ...) cleans the column you are staring at
    and leaves the one you are billing on."""
```

"Add DISTINCT until it looks sane" is the single most common wrong fix for fan-out,
by humans and models alike, and this is why it does not work.

---

## Working with the model

**Give it the contract, not the codebase.** `schema/model.md` plus the query library.
Dumping the repo into context buys you nothing here — the failure mode is bad
cardinality reasoning, not missing code.

**Ask for the test first, or at least in the same breath.** "Add a query for X, and a
test asserting it against a reference implementation computed from the CSVs." The test
is what makes the query reviewable; requesting it separately means you review the
query by eye once and then never again.

**Give it a failing test rather than a description.** A test that fails with
`assert 7 == 3` is unambiguous. "The order count seems too high" invites a plausible
guess.

**Ask what the row grain is before accepting an aggregate.** "What is one row after
this MATCH?" catches every fan-out bug in this document, and it is a question with a
checkable answer. If the answer is "one row per line" and you are counting orders, you
already know.

**Let it write the invariant checks.** Turning "every order has exactly one customer"
into the `OPTIONAL MATCH ... WHERE owners <> 1` query is mechanical, tedious, and
exactly the thing to hand off. Same for the reference implementations — they are
deliberately dumb code, and dumb code is safe to generate because the Cypher checks it
right back.

**Make it run against both engines when portability matters.** Two engines disagreeing
is free information about which of your assumptions were really assumptions. See
[`docs/engine-notes.md`](docs/engine-notes.md) — every entry there was found by
executing a query, not by reading documentation.

**Do not let it "fix" a number by adding DISTINCT.** If an aggregate looks wrong, the
row grain is wrong. Fix the grain.

---

## Layout

```
graph/
  schema/model.md              the contract
  schema/migrations/           001_.../{neo4j,kuzu}.cypher, or shared.cypher
  data/*.csv                   seed data, small enough to verify by hand
  src/gerdgraph/
    backend.py                 thin protocol over both engines
    backends/{kuzu,neo4j}_backend.py
    migrate.py                 versioned, checksummed migration runner
    ingest.py                  batched idempotent loading
    queries.py                 the query library + BROKEN_EXAMPLES
    cli.py                     migrate | status | ingest | queries | run
  tests/                       reference.py + six test modules
  docs/engine-notes.md         engine facts, each pinned by a test
```

The abstraction over the two engines is deliberately thin. It hides *connection*
differences, not *dialect* differences: read queries are shared verbatim, DDL is
written once per dialect. Smoothing over dialect differences in code is how you end up
unable to tell which engine a bug belongs to.

## Commands

```bash
python -m gerdgraph migrate                                  # apply pending migrations
python -m gerdgraph status                                   # pending / applied / CHANGED
python -m gerdgraph ingest                                   # load data/*.csv (idempotent)
python -m gerdgraph queries                                  # list the library
python -m gerdgraph run supplier_revenue_exposure            # run one
python -m gerdgraph run similar_customers --customer-id C004 # with parameters
python -m gerdgraph --json run revenue_by_category           # JSON out

make test          # embedded engine
make test-neo4j    # same suite, Neo4j via docker compose
```

## Porting this to your graph

1. Rewrite `schema/model.md` for your domain. Keep the invariants and the counting
   rule — they are the sections that do the work.
2. Replace `schema/migrations/001_core_schema/` with your DDL.
3. Point `ingest.py` at your sources. Keep MERGE-on-key and the batching.
4. Delete the queries, keep the `Query` registry and the CLI.
5. **Write `tests/reference.py` first.** It is the only part that can tell you the
   Cypher is wrong, and it is much harder to write honestly after you have seen what
   the graph returns.
