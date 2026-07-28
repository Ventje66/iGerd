# Ingestion cost model

Corrections to the 5,000-episode backfill estimate, and why the graphiti MCP
config does not implement the architecture the estimate prices.

## The arithmetic

The naive line is right: 5,000 × 1,400 tokens = 7M tokens × $5/M = **$35.00**.

The optimized line does not reconcile with its own stated unit prices.

| Line | Tokens | Stated rate | Cost |
|---|---|---|---|
| schema prefix | 5,000 × 600 = 3.0M | $0.50/M cache read | $1.50 |
| episode text | 5,000 × 800 = 4.0M | $2.50/M batch input | $10.00 |
| | | **total** | **$11.50** |

The stated total is $10.30, which is what you get at **$0.10/M** for cache
reads. That looks like the 0.1× cache-read *multiplier* being read as a
dollar price. On Opus 5 the base input rate is $5/M, so cache reads are
$0.50/M.

Two adjustments push the other way, and neither was claimed:

- Batch pricing is 50% off *all* token usage, cache reads included. If the
  whole backfill is batched, the schema line is $0.25/M → $0.75, total
  **$10.75**.
- The 600-token prefix figure is hypothetical. The real prefix in
  `extract.py` is ~830 tokens, which makes the schema line $2.08 at
  full-rate cache reads.

A 600-token prefix does clear Opus 5's 512-token cacheable minimum, but by
88 tokens. That is a thin margin for a number that moves every time someone
edits the prompt — which is why `check_cache_prefix()` asserts it.

## The term that was left out

Output is missing from the optimized column, and it is almost certainly the
largest line in the whole model. Thinking is on by default on Opus 5 and
bills as output at $25/M ($12.50/M batched). Low effort shortens thinking;
it does not remove it.

| Output per episode | Batched at $12.50/M |
|---|---|
| 300 tokens | $18.75 |
| 600 tokens | $37.50 |
| 900 tokens | $56.25 |

At any plausible figure, output exceeds the entire $11.50 input side.

This also makes the comparison uneven: the naive column carries "plus heavy
reasoning output at $25/M" while the optimized column asserts "output
minimal at low effort" and stops. The two columns are not measuring the same
thing.

Worth noticing what that hides. Dropping from high to low effort acts almost
entirely on output tokens — so the single biggest saving in the plan lands
in the one column the model doesn't total. Illustratively, at 1,200 output
tokens/episode naive and 400 batched:

| | Input | Output | Total |
|---|---|---|---|
| Naive | $35.00 | $150.00 | $185.00 |
| Optimized | $11.50 | $25.00 | $36.50 |

Those output figures are guesses. **Measure before extrapolating**: run 20
episodes, read `usage.output_tokens`, then multiply. The input side is known
to within a few percent; the output side currently is not known at all.

## The config does not implement this

`.mcp.json` and the estimate describe different systems. The estimate prices
a cached prefix, low effort, and batching. The graphiti MCP server does
none of the three.

**Effort cannot be set.** There is no `MODEL_EFFORT` environment variable —
graphiti reads `NEO4J_*`, the provider API keys, `SEMAPHORE_LIMIT`,
`GRAPHITI_TELEMETRY_ENABLED`, and the Azure/FalkorDB/Voyage settings, and
nothing else. An unrecognized key in the `env` block is inert, so extraction
through graphiti runs at Opus 5's default `high` effort. That is the exact
case `CLAUDE.md` lists under **Never**.

This is the same failure mode as `extra_headers={"effort": "low"}` in the
original extraction call: a plausible-looking knob in a place that accepts
arbitrary keys and ignores the ones it doesn't know.

**Provider defaults to OpenAI.** Graphiti selects its client from
`llm.provider` (config.yaml) or `--llm-provider`, not from the model string.
Naming a Claude model without setting the provider sends `claude-opus-5` to
OpenAI. Anthropic support is also an optional extra — a bare
`uvx graphiti-mcp` does not install it.

**No batching, and there could not be.** Graphiti has no Batches API
integration, and an MCP server is the wrong shape for one: batches are
asynchronous with up to a 24-hour turnaround, while an MCP tool call is a
synchronous request/response. You cannot get batch pricing through a
tool call, regardless of configuration.

**No prompt caching.** Graphiti sets no `cache_control` breakpoint.

## Where that leaves the two paths

The routing policy already separates these; the estimate merges them.

- **Live ingestion** — one episode as it arrives. Synchronous is correct,
  graphiti fits, and there is no batch discount to lose. The cost is the
  naive rate on a single episode, which is a rounding error.
- **Historical backfill** — 5,000 episodes. This is what the estimate
  prices, and it must not run through an MCP tool call. It goes through
  `extract.py`'s `submit_backfill`, which is where the cached prefix, low
  effort, and batch rate actually exist.

So the estimate is a reasonable target — it just describes `extract.py`, not
the MCP server. If graphiti is to own extraction as well, the effort rule
needs an upstream change to graphiti; until then, that path runs at high
effort and the policy is not being enforced.
