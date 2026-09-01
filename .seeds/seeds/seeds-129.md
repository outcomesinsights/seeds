---
id: seeds-129
title: "Concern: source documents may span multiple projects"
status: captured
type: concern
created_at: 2026-03-12T20:01:27.537340+00:00
updated_at: 2026-03-12T20:01:27.537348+00:00
tags:
  - architecture
  - source-materials
  - scoping
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.075793+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.905214+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.653821+00:00
  - target_id: seeds-181.2
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.402055+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.543013+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The problem:** A single source document (e.g., a meeting transcript with a boss) may contain seeds relevant to multiple different projects. Only a small portion of the transcript may be relevant to the project whose seeds database is being updated.

**Implications:**
- The gleaning/extraction process must be project-aware: given what THIS project cares about, what's relevant in this document?
- Storing the full document in one project's .seeds/ means the other project doesn't have it
- Clipping only the relevant section means we lose context and can't re-glean later
- The same document might need to be ingested into multiple seeds databases separately

**Possible approaches:**
1. Full document stored once, each project extracts its own seeds from it
2. Clip relevant sections per-project (lossy, can't re-glean)
3. Shared source library outside any single project (new concept: global seeds sources)
4. Accept duplication: each project stores a copy if it needs one

**This is related to but distinct from the privacy concern — even within 'safe' documents, scoping is needed.**
