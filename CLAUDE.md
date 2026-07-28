# Graph routing

Two call sites, two profiles. Never one shared configuration.

## Ingestion (writing to the graph)

- Model `claude-opus-5`, `output_config={"effort": "low"}`.
- The extraction schema is a cached prefix. Freeze it: no f-strings, no
  timestamps, no per-episode IDs above the `cache_control` breakpoint.
- **The prefix must be at least 512 tokens or `cache_control` is silently
  ignored** — no error, no cache, `cache_creation_input_tokens` stays 0.
  Assert the floor at startup rather than discovering it in a bill.
- Historical backfills go through the Message Batches API. Never loop
  `messages.create` over a backlog synchronously.

## Traversal (querying the graph)

- Model `claude-opus-5`, `output_config={"effort": "high"}`; `max` for deep
  multi-hop.
- Retrieval is a required step, not an option. Pull the relevant subgraph
  first, then reason only over those facts.
- Every answer cites the specific edges it used.

### Known gap: graphiti cannot honour the effort rule

The graphiti MCP server exposes no effort setting — there is no
`MODEL_EFFORT` variable, and unrecognised keys in an `env` block are inert.
Extraction routed through it therefore runs at Opus 5's default `high`
effort, which the Never list below forbids. It also does no prompt caching
and no batching.

Until that changes upstream, graphiti is the live-ingest and storage path
only. Historical backfill goes through `extract.py:submit_backfill`, which
is where the cached prefix, low effort, and batch rate actually exist. See
`docs/ingestion-costs.md`.

## Never

- Extraction at high effort. Canonicalization and date normalization are
  mechanical; depth buys nothing and costs tokens.
- Traversal at low effort. Low effort scopes work to what was literally
  asked, which on a multi-hop question means a shallow answer that looks
  complete.
- One effort setting shared across both call sites.

## Note on effort and caching

An earlier version of this policy said changing effort mid-session
invalidates the cache. It does not, and the reasoning matters because the
wrong version pushes you toward a single shared effort — which breaks the
routing above.

Caching is a prefix match over the rendered `tools → system → messages`.
`output_config.effort` is not part of that rendering, and it does not appear
in the documented invalidation hierarchy. The closest documented analog,
toggling `thinking` on or off, preserves both the tools and system cache.

The rule that survives is structural, not cache-driven: ingestion and
traversal are separate call sites with different system prefixes and
therefore different cache entries. Effort is fixed per call site because
each site has one job — not because varying it would cost you a cache hit.

What *does* invalidate everything is a model switch. Keep both sites on
`claude-opus-5`; if a sub-task needs a cheaper model, give it its own call
site rather than switching models inside an existing one.
