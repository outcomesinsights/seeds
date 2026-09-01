---
id: seeds-175.5
title: "OPEN — Kellogg framing: 'sidesteps the debate' vs 'picks the tokens side'"
status: resolved
type: question
parent: seeds-175
created_at: 2026-06-17T16:40:42.187604+00:00
updated_at: 2026-08-31T20:02:43.237343+00:00
resolved_at: 2026-06-17T16:47:38.172874+00:00
resolution: "Reframe 'sidesteps' to: seeds comes down on the tokens side at the layer that matters (delivery = reassembled markdown the agent reads); SQLite + typed links are storage/retrieval bookkeeping, the kind Kellogg tolerates in an issue tracker, not a graph the model reasons over. Add an honest nod that whether even that light structure helps or fights the agent is still open (seeds-170/174)."
tags:
  - blog
  - kellogg
  - structure
  - open
  - architecture
relationships:
  - target_id: seeds-170
    rel_type: relates-to
    created_at: 2026-06-17T16:41:25.204632+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Confirmed against the live article: Kellogg has a 'Bad ideas' section naming knowledge graphs and SQL-backed memory as things to avoid (the LLM weights do not know the schema). seeds stores deliberation in SQLite with typed relationships — the thing he side-eyes — so citing him as SUPPORT for 'seeds sidesteps the debate' is backwards. @aguynamedryan's nuance to resolve: Kellogg is about how you REPRESENT info to an IN-FLIGHT agent (delivery/runtime), whereas the post's concern is how seeds STORES deliberation (persistence). At delivery seeds hands the agent reassembled markdown (tokens); the SQLite/typed-relationship structure is storage-layer. So seeds arguably AGREES with Kellogg at delivery while using light structure at storage — it picked the tokens side, did not sidestep. Decide exact reframing. Maps to seeds-170 and seeds-174.
