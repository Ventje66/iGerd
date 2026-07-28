// 001_core_schema — Neo4j
//
// Neo4j is schema-optional: nodes and properties spring into existence on write.
// The only thing that must be declared is what protects you — uniqueness
// constraints (which also give you the index that MERGE needs to not be O(n)).
//
// Create constraints BEFORE the first ingest. A MERGE on an unindexed property
// scans every node of that label, so a load that should take seconds takes hours,
// and a concurrent load without the constraint will happily create duplicates.

CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
FOR (c:Customer) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT sales_order_id_unique IF NOT EXISTS
FOR (o:SalesOrder) REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT product_sku_unique IF NOT EXISTS
FOR (p:Product) REQUIRE p.sku IS UNIQUE;

CREATE CONSTRAINT supplier_id_unique IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.id IS UNIQUE;

// Not a key, but every "orders in a window" query filters on it.
CREATE INDEX sales_order_placed_on IF NOT EXISTS
FOR (o:SalesOrder) ON (o.placed_on);
