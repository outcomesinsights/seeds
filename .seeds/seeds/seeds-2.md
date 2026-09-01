---
id: seeds-2
title: "AI discoverability: how can AI quickly know what's in seeds?"
status: captured
type: question
created_at: 2026-01-28T05:54:01.142491+00:00
updated_at: 2026-05-18T15:58:09.393997+00:00
tags:
  - ai-ux
  - architecture
relationships:
  - target_id: seeds-13
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.142491+00:00
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.142491+00:00
  - target_id: seeds-89
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.142491+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.066571+00:00
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.942995+00:00
  - target_id: seeds-142.1
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.027305+00:00
  - target_id: seeds-142.3
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.211815+00:00
  - target_id: seeds-vo56
    rel_type: relates-to
    created_at: 2026-08-12T13:25:46.227486+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From discussion.md: 'How can we get AI to be able to know what is in a given seed or set of seeds easily without overloading its context window?'

Possible approaches identified:
- Tags: Limited predefined set per project for consistency
- Summaries: Auto-generated one-liners for each seed
- Manifests: Index of all seeds with metadata
- Embeddings: Semantic search to find relevant seeds

Tag strategy: A limited predefined set could ensure consistency, make it easier to find interrelated seeds, and help AI categorize without inventing new tags.



---

**Concrete answer emerging from CSC production usage (2026-04 to 2026-05) — see seeds-142 for the use-case evidence:**

Three primitives, none of which currently exist, address this question together:

1. **Project digest in `seeds prime`** — see seeds-87 (now has concrete design proposal)
2. **`seeds suggest <text>`** — purpose-built dedup query, FTS5 + tag-overlap ranking. New sibling seed.
3. **ID-reference validation on write** — catches hallucinated cross-refs (silently degrades discoverability). New sibling seed.

The CSC case (96 seeds) showed the cold-start discovery cost is real: 3-6 commands per session and inconsistent patterns across sessions. The above primitives, taken together, would let Claude enter a project and immediately know the shape of what's there.
