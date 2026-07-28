# iGerd

## [`graph/`](graph/) — graph engineering with Opus 5

A working Cypher scaffold plus the method that goes with it: model → migrate →
ingest → query → verify, built so that model-written Cypher is safe to accept
because something other than your eyes is checking it.

```bash
cd graph
pip install -e ".[dev]"
python -m gerdgraph migrate && python -m gerdgraph ingest
python -m gerdgraph run revenue_by_customer --limit 4
pytest
```

Runs on an embedded engine by default — no server, no container. `docker compose up
-d` and `GRAPH_BACKEND=neo4j` runs the same code and the same tests against Neo4j.

Start with [`graph/README.md`](graph/README.md).
