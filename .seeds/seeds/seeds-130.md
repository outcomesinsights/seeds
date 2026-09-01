---
id: seeds-130
title: "Project-aware gleaning: LLM needs project context to extract relevant seeds"
status: captured
type: exploration
created_at: 2026-03-12T20:01:43.553521+00:00
updated_at: 2026-03-12T20:01:43.553528+00:00
tags:
  - architecture
  - gleaning
  - ai-ux
  - context
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.192541+00:00
  - target_id: seeds-129
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.905214+00:00
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.980356+00:00
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.066571+00:00
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.771910+00:00
  - target_id: seeds-142.1
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.125048+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.547276+00:00
  - target_id: seeds-181.1
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.185079+00:00
  - target_id: seeds-181.3
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.638124+00:00
  - target_id: seeds-182
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.314421+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The challenge:** When an LLM reviews a source document to extract seeds, it needs to know what the project cares about. Seeds for the seeds project are different than seeds for other projects. How do we convey project context tersely but thoroughly?

**What the LLM needs to know:**
- High-level project purpose/domain
- What kinds of seeds already exist (to avoid duplicates, to find updates)
- What themes/topics are being actively explored
- What questions are currently open

**The tension:** As a project grows, its seed database grows. We can't dump 152 seeds into a context window for every document ingestion. Need a compressed representation.

**Possible approaches:**
1. Use `seeds prime` output — already designed for this purpose
2. Tag-based summary: list all unique tags as a project profile
3. Active seeds only: only show exploring/captured status seeds
4. Hierarchical summary: top-level seeds with child counts
5. Embeddings-based: find seeds semantically similar to the source document, only show those

**Key insight from user:** This perspective changes as the project evolves. A document gleaned early in the project may yield different seeds when re-gleaned later with a richer understanding of the project's concerns. This is an argument for keeping source documents available for re-ingestion.

**Relationship to dynamic prime (seed-6bb3):** The dynamic prime concept is essentially this — injecting live project state into AI context. Gleaning is one consumer of that state.
