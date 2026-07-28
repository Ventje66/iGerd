.PHONY: help install rebuild test test-neo4j lint clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-12s %s\n", $$1, $$2}'

install:  ## install the package plus dev/neo4j extras
	pip install -e ".[dev,neo4j]"

rebuild:  ## drop the embedded db, migrate, ingest
	rm -rf .kuzu
	python -m gerdgraph migrate
	python -m gerdgraph ingest

test:  ## run the suite against the embedded engine
	pytest

test-neo4j:  ## run the same suite against a running Neo4j (docker compose up -d)
	GRAPH_BACKEND=neo4j pytest

clean:
	rm -rf .kuzu .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
