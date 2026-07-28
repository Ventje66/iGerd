// 001_core_schema — Kuzu
//
// Kuzu is schema-first: every label is a declared node table and every
// relationship type is a declared rel table with a fixed FROM/TO pair.
// The PRIMARY KEY is the uniqueness constraint and the index in one.
//
// This is the same model as neo4j.cypher, stated in the dialect that enforces it
// up front instead of at write time. Writing both is the point: if the two files
// ever describe different graphs, one of them is a bug.

CREATE NODE TABLE Customer(
    id STRING,
    name STRING,
    segment STRING,
    country STRING,
    PRIMARY KEY(id)
);

CREATE NODE TABLE SalesOrder(
    id STRING,
    placed_on STRING,
    channel STRING,
    PRIMARY KEY(id)
);

CREATE NODE TABLE Product(
    sku STRING,
    name STRING,
    unit STRING,
    PRIMARY KEY(sku)
);

CREATE NODE TABLE Supplier(
    id STRING,
    name STRING,
    country STRING,
    PRIMARY KEY(id)
);

CREATE REL TABLE PLACED(FROM Customer TO SalesOrder);

CREATE REL TABLE CONTAINS(
    FROM SalesOrder TO Product,
    qty INT64,
    unit_price DOUBLE
);

CREATE REL TABLE SUPPLIED_BY(
    FROM Product TO Supplier,
    lead_time_days INT64
);
