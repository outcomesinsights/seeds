---
id: seeds-89
title: "Knowledge accumulation: formalizing investigation capture as a seeds pattern"
status: captured
type: exploration
created_at: 2026-02-26T16:37:32.179511+00:00
updated_at: 2026-03-11T20:50:14.643752+00:00
tags:
  - knowledge
  - investigation
  - workflow
  - pattern
relationships:
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.142491+00:00
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.882137+00:00
  - target_id: seeds-12.2
    rel_type: relates-to
    created_at: 2026-02-24T17:05:24.873205+00:00
  - target_id: seeds-116
    rel_type: relates-to
    created_at: 2026-02-26T16:37:32.179511+00:00
  - target_id: seeds-90
    rel_type: questioned-by
    created_at: 2026-02-26T16:41:49.863036+00:00
  - target_id: seeds-91
    rel_type: questioned-by
    created_at: 2026-02-26T16:41:51.112229+00:00
  - target_id: seeds-126
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.293714+00:00
  - target_id: seeds-184
    rel_type: relates-to
    created_at: 2026-06-24T16:47:31.897568+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Observed pattern:** When exploring a new tool, library, or domain, the AI spends significant time (5-10 min) reading documentation, scraping code, and building understanding. This accumulated knowledge is valuable and shouldn't require re-scraping in future sessions.

**Current behavior (ad hoc):**
- Ask Claude to capture findings into a file (markdown document)
- Store alongside the project (e.g., seeds/ has files about beads, deliberation software)
- Reference these files in future sessions to avoid re-investigation

**Examples of this pattern:**
- This seeds project: comprehensive notes on beads, deliberation tools, domain research
- Other projects: tool evaluations, API documentation summaries, architecture deep-dives
- Any time Claude does a multi-minute investigation and you want to preserve the result

**What formalization could look like:**
- A seed type or tag for "investigation" or "knowledge base" items
- Seed content holds the executive summary; an attached document holds the deep knowledge
- The \`prime\` command could surface relevant knowledge documents for the current session context
- Seeds could track the provenance: when was this knowledge gathered, from what sources, how stale is it?
- A \`seeds investigate\` command that creates a seed + kicks off research + captures findings

**Relationship to seeds' identity:**
This strengthens the "seeds is for thinking, beads is for doing" distinction. Knowledge accumulation is a *deliberation* activity — understanding the landscape before deciding what to build. It's not a task to track in beads; it's context that informs future decisions.

**Open questions:**
- Should the knowledge document be part of the seed content, or a separate linked artifact?
- How do you handle staleness? Knowledge about a tool at v0.50 may be wrong at v0.56.
- Is this seeds' job or a separate "knowledge base" tool? (Same question as templates — and beads answered that by making molecules a core feature.)


---
**Refined insight (Feb 2026): Investigation output IS source material.**

The distinction between "source materials" (seed-1def) and "knowledge accumulation" collapses: the expertise document generated from an investigation becomes a source material for future deliberation. The workflow is circular:

1. Question or idea triggers investigation
2. Investigation produces an expertise document (captured knowledge)
3. That document immediately becomes an input for seed evaluation ("given what we just learned, how does this affect our existing seeds?")
4. Future sessions reference it as source material rather than re-investigating

**What seeds should formalize:**
- When an investigation is performed (large exploration, documentation scraping, tool research), seeds should expect and facilitate the capture of findings into a durable document
- That document should be treated as a source material going forward — referenced, not regenerated
- The document should be explicitly invalidatable: "this section seems wrong, re-investigate X" — targeted correction rather than wholesale re-research
- The seed that triggered the investigation should link to the resulting document

**What this is NOT:**
- Not a cache or memoization (it's curated knowledge, not raw data)
- Not immutable (it can be corrected, but corrections are explicit and targeted)
- Not auto-generated (the AI captures what it learned, with judgment about what matters)

**The pattern:** investigate → capture → reference → correct-as-needed. Seeds already does the first two ad hoc. Formalizing it means seeds becomes the system of record for "what do we know about X?" — not just "what are we thinking about X?"


---
**Additional pattern: plan documents as knowledge artifacts (Feb 2026).**

Even before seeds is initialized for a project, there's often a plan document — an initial conversation with Claude working through structure, requirements, approach. This document:
- Contains deliberation that predates the seeds database
- Gets broken into individual seeds when the project formalizes
- Is itself a knowledge artifact worth preserving and referencing
- Is vulnerable to being overwritten by Claude (not under version control, terrifying)

The workflow: plan document → seeds extraction → ongoing deliberation. The plan document is the *original* source material, and seeds should be able to reference it as context for why certain seeds exist.

**On source tracking (provenance):**
Tracking which sources a seed's knowledge came from (URLs, documents, conversations) would be valuable but is explicitly deferred for now. The priority is: don't lose the knowledge artifacts themselves. Provenance tracking is a future enrichment, not a prerequisite.
