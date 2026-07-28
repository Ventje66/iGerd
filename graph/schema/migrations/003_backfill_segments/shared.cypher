// 003_backfill_segments — both dialects
//
// A migration with no `neo4j.cypher` / `kuzu.cypher` falls back to `shared.cypher`.
// Pure data migrations usually can: it is DDL that diverges, not MATCH/SET.
//
// On a fresh database this touches nothing, because ingest runs after migrate and
// already sets `segment`. It exists for the databases that are already out there
// with the property missing. That is the normal shape of a data migration: a no-op
// in CI and the whole point in production.

MATCH (c:Customer)
WHERE c.segment IS NULL
SET c.segment = 'unknown';
