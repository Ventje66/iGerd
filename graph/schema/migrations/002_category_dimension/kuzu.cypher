// 002_category_dimension — Kuzu
//
// Adding a dimension is real DDL here: a new node table, a new rel table, and an
// ALTER for the new Product property. Because the property has a DEFAULT, existing
// rows are backfilled by the engine and no separate data migration is needed.

CREATE NODE TABLE Category(
    name STRING,
    PRIMARY KEY(name)
);

CREATE REL TABLE IN_CATEGORY(FROM Product TO Category);

ALTER TABLE Product ADD hazard_class STRING DEFAULT 'none';
