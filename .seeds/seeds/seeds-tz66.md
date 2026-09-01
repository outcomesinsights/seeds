---
id: seeds-tz66
title: Is jot a stupid idea? The empty-body count says no — six of the eight bare ideas are test fixtures polluting the design DB
status: captured
type: question
created_at: 2026-08-31T22:20:54.749473+00:00
updated_at: 2026-09-01T00:46:53.981237+00:00
tags:
  - jot
  - capture
  - friction
  - thesis
  - test-pollution
  - measured
  - 2026-08-31
relationships:
  - target_id: seeds-176.9
    rel_type: relates-to
    created_at: 2026-08-31T22:21:02.825406+00:00
  - target_id: seeds-195
    rel_type: relates-to
    created_at: 2026-08-31T22:21:02.943782+00:00
  - target_id: seeds-02ur
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.059935+00:00
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.188995+00:00
  - target_id: seeds-rlc2
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.322211+00:00
  - target_id: seeds-not2
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.630737+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, 2026-08-31, on seeing that 31 of 312 seeds have no body: **"almost feels like jot is a stupid idea."**

The worry is real and worth stating plainly, because it goes at the project's thesis. seeds claims *the deliberation is the artifact* (seeds-176.9). A jotted seed is a title and nothing else — it carries no deliberation at all. So `jot` is the one verb that produces the one shape of seed containing none of what seeds exists to hold. If jotted seeds mostly never grow, `jot` is optimising capture volume over capture value, and the tool's headline feature is working against its thesis.

## Measured the same day, and it does NOT support the worry

31 of 312 seeds have an empty body. Split by type, that number falls apart:

- **23 are question-type**, median age 100 days, 20 still `captured`. For a question the title IS the content — "Is spec-ready a new lifecycle state, or could it be modeled as resolution?" is a complete question. An unexplored question sitting in the backlog is the backlog working, not a failed capture.
- **8 are idea-type** — and six of those are **test fixtures somebody left in the real design database**: seeds-71, seeds-71.1, seeds-71.1.1, seeds-71.1.1.1 and seeds-71.2 are a nesting demo ("Test parent seed for nesting demo", "Child seed (depth 1)", "Grandchild (depth 2)", "Great-grandchild (depth 3)"), and seeds-136 is "Test sequential ID generation", already abandoned. All 205-214 days old. A seventh, seeds-68 "Web UI: Render markdown content", is dead scope — the web UI was killed in seeds-rlc2.

**That leaves exactly ONE genuine title-only idea in 214 days of use: seeds-26.**

So the evidence says the opposite of the worry. `jot` is not producing a drift of fragments that never grow; one abandoned fragment in seven months is a rounding error. What made the number look alarming was debris, and the debris has a different cause.

## The finding that actually falls out: the design database has test pollution in it

Six fixtures are sitting in `.seeds/` — precisely what this project's CLAUDE.md forbids in as many words ("The `.seeds/` directory in this project contains real design data ... It is NOT a test database"). They predate that instruction, which is presumably why the instruction exists. Cleanup belongs with seeds-02ur's 36 orphaned question rows: both are migration/experiment debris nobody noticed for months, and the storage conversion is the moment they either get dropped or get carried forward into the new format forever.

## Why this validates the empty-body ruling rather than undermining it

@aguynamedryan ruled the same day that an empty body is a **smell, not a violation** (seeds-sdhc.2, and plans/storage-overhaul.md). Under that ruling `check --smells` would have listed these six fixtures as "no body, no growth, 205 days" — which is exactly how you would have found them. The smell tier earns its keep here on its first realistic use, and the standing cost of ~31 entries is mostly 23 legitimately-open questions plus debris that is about to be deleted.

## What stays genuinely open

Nothing about `jot` needs changing on this evidence. The residual question is narrower and is about a **different** verb: seeds-195 asks where a "deepening" pass belongs in the lifecycle, and explicitly rules it out of the low-friction jot path. That remains the right place for the concern — the answer to "a thought was captured thin and never fleshed out" is a pass that revisits, not friction at the point of capture.

Relates to seeds-176.9, seeds-195, seeds-02ur, seeds-sdhc.2, seeds-rlc2.

NOTE (2026-08-31): @aguynamedryan ruled that the six fixtures named above — seeds-71, seeds-71.1, seeds-71.1.1, seeds-71.1.1.1, seeds-71.2 and seeds-136 — are DROPPED at the storage conversion (bead seeds-4co.6). After conversion those IDs cite files that no longer exist. They are kept in the text above deliberately, because they are the evidence for this seed's conclusion, and they remain recoverable from git history. They were never relationship edges, so this is not a broken link — but an edit to this seed will trip the hallucinated-ID guard, and --allow-unknown-refs is the right answer rather than deleting the evidence.
