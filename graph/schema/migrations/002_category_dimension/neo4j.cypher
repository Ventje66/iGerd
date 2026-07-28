// 002_category_dimension — Neo4j
//
// The new label needs a key constraint. The new Product property needs nothing
// structural — but it does need a backfill, because Neo4j has no column DEFAULT.
// Kuzu's ALTER ... DEFAULT does this for free; here it is an explicit write.
//
// Same migration, different amount of work per engine. That asymmetry is normal;
// hiding it behind a "portable" abstraction is how people end up with a graph
// whose two deployments disagree.

CREATE CONSTRAINT category_name_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.name IS UNIQUE;

MATCH (p:Product)
WHERE p.hazard_class IS NULL
SET p.hazard_class = 'none';
