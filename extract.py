"""Knowledge-graph extraction from episodic text via the Claude API.

Run over a stream of episodes; each call returns entities and time-stamped
edges. The system prompt is a frozen cache prefix — see CACHING below.
"""

import json
import os

import anthropic

client = anthropic.Anthropic()

MODEL = "claude-opus-5"

# CACHING
# -------
# Prompt caching is a prefix match, and the minimum cacheable prefix on
# Opus 5 is 512 tokens. A shorter prefix does not error — it silently
# doesn't cache, and usage.cache_creation_input_tokens stays 0.
#
# This prompt is deliberately long enough to clear that floor. The length
# is not padding: the type taxonomy and the worked example are what keep
# entity naming and edge dating consistent across episodes.
#
# Two rules keep the cache alive:
#   1. Every byte here must be identical on every call. No f-strings, no
#      datetime.now(), no per-episode IDs. Volatile content goes in the
#      user turn, after the breakpoint.
#   2. Don't change MODEL mid-run. Caches are model-scoped.
# Verify with check_cache_prefix() below before trusting the cost model.
EXTRACTION_SYSTEM = """You extract a knowledge graph from a single episode of text.

An episode is one observation at one point in time. You are building an
incremental graph: many episodes will be processed independently and merged
downstream, so your output must be canonical and self-consistent rather than
locally convenient.

ENTITIES

Every entity has a name, a type, and a description.

Names are canonical. Resolve aliases, nicknames, honorifics, and shortened
forms to one preferred surface form and use it everywhere in your output,
including inside edges. "Buzz Aldrin" and "Edwin Aldrin" are one entity.
"IBM" and "International Business Machines" are one entity. Prefer the form
the world most commonly uses, not the form the text happens to use.

Types are drawn from this closed set:
  person        an individual human
  organization  company, agency, team, band, institution
  location      place, region, facility, address
  event         something that happened at a time
  product       artifact, model, software, vehicle, publication
  concept       anything else worth a node

Descriptions are one sentence, and describe the entity as the text presents
it. Do not import outside knowledge into the description.

Do not create an entity for something merely mentioned in passing with no
attributes and no relationships. A graph node needs to earn its place.

EDGES

Every edge has a source, a target, a relation, and a valid_from.

source and target are canonical entity names. Both must appear in your
entities list. Never write an edge that dangles.

relation is a lowercase snake_case verb phrase reading source-to-target:
worked_at, founded, located_in, married_to, acquired, authored, member_of.
Reuse relation names across episodes rather than inventing near-synonyms.

valid_from is when the relationship began, in ISO-8601 (YYYY-MM-DD, or
YYYY-MM when the day is unknown, or YYYY when only the year is). Resolve
relative expressions against reference_time: "last Tuesday", "in 1969",
"three years ago" all become concrete dates. If the text gives no basis for
a start date at all, use null — do not guess, and do not default to
reference_time.

Extract only relations the text states or directly implies. Do not add
relationships you know to be true from outside the text. An episode that
supports no edges should return an empty edges list; that is a valid result.

EXAMPLE

reference_time: 1969-07-21

Buzz Aldrin followed Neil Armstrong onto the lunar surface. Both men had
flown for NASA since the Gemini program began in 1961.

{
  "entities": [
    {"name": "Edwin Aldrin", "type": "person", "description": "Astronaut who walked on the Moon after Neil Armstrong."},
    {"name": "Neil Armstrong", "type": "person", "description": "Astronaut who was first onto the lunar surface."},
    {"name": "NASA", "type": "organization", "description": "Space agency the astronauts flew for."}
  ],
  "edges": [
    {"source": "Edwin Aldrin", "target": "NASA", "relation": "worked_at", "valid_from": "1961"},
    {"source": "Neil Armstrong", "target": "NASA", "relation": "worked_at", "valid_from": "1961"}
  ]
}

Note the canonicalization to "Edwin Aldrin", the year-only valid_from, and
the absence of any edge asserting the moonwalk itself — the text describes
an ordering, not a dated relationship between the two men."""

# Structured outputs: the shape is enforced by the API rather than requested
# in prose, so the response is always parseable JSON matching this schema.
# Every object needs additionalProperties: false, and every property must be
# listed in required — optionality is expressed with an explicit null branch.
GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": [
                            "person",
                            "organization",
                            "location",
                            "event",
                            "product",
                            "concept",
                        ],
                    },
                    "description": {"type": "string"},
                },
                "required": ["name", "type", "description"],
                "additionalProperties": False,
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation": {"type": "string"},
                    "valid_from": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                    },
                },
                "required": ["source", "target", "relation", "valid_from"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entities", "edges"],
    "additionalProperties": False,
}


class ExtractionError(RuntimeError):
    """The model did not return a usable graph for this episode."""


def extract(episode_text, occurred_at):
    """Extract a knowledge graph from one episode.

    Returns {"entities": [...], "edges": [...]}. Raises ExtractionError if
    the model refused or ran out of output budget.
    """
    response = client.messages.create(
        model=MODEL,
        # Thinking is on by default on Opus 5, and max_tokens caps thinking
        # plus response text together. Size this for both, or the JSON gets
        # truncated mid-object.
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": EXTRACTION_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        # effort is a request parameter, not a header. Low effort is the
        # right lever for mechanical work — it shortens thinking without
        # turning it off, which on Opus 5 is the failure-prone setting.
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": GRAPH_SCHEMA},
        },
        # Volatile content lives here, after the cache breakpoint.
        messages=[
            {
                "role": "user",
                "content": f"reference_time: {occurred_at}\n\n{episode_text}",
            }
        ],
    )

    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None)
        raise ExtractionError(f"refused (category={category})")

    if response.stop_reason == "max_tokens":
        raise ExtractionError(
            "hit max_tokens; output is truncated. Raise max_tokens or split "
            "the episode."
        )

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def check_cache_prefix():
    """Confirm the frozen prefix actually caches. Run once at startup.

    A prefix under 512 tokens is a silent no-op on Opus 5 — no error, no
    cache, and no signal except cache_read_input_tokens staying 0.
    """
    counted = client.messages.count_tokens(
        model=MODEL,
        system=[{"type": "text", "text": EXTRACTION_SYSTEM}],
        messages=[{"role": "user", "content": "x"}],
    ).input_tokens

    if counted < 512:
        raise RuntimeError(
            f"prefix is {counted} tokens, under Opus 5's 512-token minimum — "
            "cache_control will be silently ignored"
        )
    return counted


if __name__ == "__main__":
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SystemExit("set ANTHROPIC_API_KEY (or run `ant auth login`)")

    print(f"cache prefix: {check_cache_prefix()} tokens")

    episodes = [
        ("Ada Lovelace began corresponding with Charles Babbage about the "
         "Analytical Engine.", "1833-06-05"),
        ("She published her notes on the engine, including what is now "
         "considered the first algorithm.", "1843-10-01"),
    ]

    for text, occurred_at in episodes:
        graph = extract(text, occurred_at)
        print(json.dumps(graph, indent=2))
