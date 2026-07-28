# Graph model — building-materials distributor

This file is the **contract**. It is the single thing you paste into a model's context
before asking for Cypher. If a query contradicts this file, the query is wrong.

Keep it accurate. A stale model doc produces confidently wrong Cypher, and that failure
mode is much more expensive than a missing index.

## Nodes

| Label             | Key         | Properties                                                | Notes |
|-------------------|-------------|-----------------------------------------------------------|-------|
| `Customer`        | `id`        | `name`, `segment` (`pro` \| `retail` \| `unknown`), `country` | A billing account, not a person. |
| `SalesOrder`      | `id`        | `placed_on` (ISO date string), `channel`                   | Named `SalesOrder`, **not** `Order` — `ORDER` is a reserved word in Cypher parsers. |
| `Product`         | `sku`       | `name`, `unit`, `hazard_class`                             | `hazard_class` defaults to `'none'`. |
| `Supplier`        | `id`        | `name`, `country`                                          | |
| `Category`        | `name`      | —                                                          | Key *is* the name; there is no separate id. |
| `SchemaMigration` | `version`   | `name`, `checksum`, `applied_at`                           | Bookkeeping, written only by the migration runner. Never query it in application code. |

## Relationships

| Pattern                                            | Cardinality        | Properties |
|----------------------------------------------------|--------------------|------------|
| `(:Customer)-[:PLACED]->(:SalesOrder)`             | 1 customer : N orders | — |
| `(:SalesOrder)-[:CONTAINS]->(:Product)`            | N : M              | `qty` (int), `unit_price` (float) |
| `(:Product)-[:SUPPLIED_BY]->(:Supplier)`           | 1 product : 1 supplier (today) | `lead_time_days` (int) |
| `(:Product)-[:IN_CATEGORY]->(:Category)`           | 1 product : 1 category | — |

`CONTAINS` **is** the order line. There is no `OrderLine` node: a line has no identity of
its own and is never referenced from anywhere else, so it stays an edge. If lines ever need
their own history or references, promote the edge to a node — that is a migration, not a
query change.

## Invariants

These hold after every successful `migrate` + `ingest`. Tests assert them.

1. `id` / `sku` / `name` keys are unique per label.
2. Every `SalesOrder` has exactly one inbound `PLACED`.
3. Every `SalesOrder` has at least one `CONTAINS`.
4. `qty > 0` and `unit_price >= 0` on every `CONTAINS`.
5. A `Product` may have no supplier (not yet sourced) but never more than one.
6. Line revenue is `qty * unit_price`. There is no discount field — do not invent one.

## Counting rule (read this before writing any aggregate)

Revenue always comes from `CONTAINS` edges:

```cypher
sum(line.qty * line.unit_price)
```

If a query matches a second one-to-many branch in the same `MATCH` (say, both
`CONTAINS` and `IN_CATEGORY` fan-outs), the `CONTAINS` rows are multiplied and the
sum silently inflates. Aggregate first, join second. See `graph/README.md` §
"The bug that gets shipped".
